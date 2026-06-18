import json
import time
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import defaultdict, OrderedDict


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HISTORY_FILE = DATA_DIR / "command_history.json"
FEEDBACK_FILE = DATA_DIR / "suggestion_feedback.json"
USER_PROFILES_FILE = DATA_DIR / "user_profiles.json"


class LRUCache:
    def __init__(self, max_size: int = 512, ttl: float = 60.0):
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[object]:
        with self._lock:
            if key not in self._cache:
                return None
            value, ts = self._cache[key]
            if time.time() - ts > self._ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def put(self, key: str, value: object) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            self._cache[key] = (value, time.time())
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class TrieNode:
    __slots__ = ('children', 'commands', 'is_end')

    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.commands: List[str] = []
        self.is_end: bool = False


class CommandTrie:
    def __init__(self):
        self.root = TrieNode()
        self._all_commands: List[str] = []

    def insert(self, command: str) -> None:
        node = self.root
        tokens = command.lower().split()
        for token in tokens:
            if token not in node.children:
                node.children[token] = TrieNode()
            node = node.children[token]
            if len(node.commands) < 50:
                node.commands.append(command)
        node.is_end = True
        if command not in self._all_commands:
            self._all_commands.append(command)

    def search_prefix(self, prefix: str, limit: int = 20) -> List[str]:
        if not prefix or not prefix.strip():
            return self._all_commands[:limit]
        tokens = prefix.lower().split()
        node = self.root
        for token in tokens:
            if token not in node.children:
                partial_matches = self._partial_token_match(token, limit)
                return partial_matches
            node = node.children[token]
        return node.commands[:limit]

    def _partial_token_match(self, partial_token: str, limit: int) -> List[str]:
        results = []
        partial = partial_token.lower()
        node = self.root
        for child_key in node.children:
            if child_key.startswith(partial):
                child_node = node.children[child_key]
                results.extend(child_node.commands[:limit])
                if len(results) >= limit:
                    break
        return results[:limit]


COMMAND_CATEGORIES = {
    "docker": [
        "docker ps -a",
        "docker images",
        "docker logs --tail 100",
        "docker-compose up -d",
        "docker-compose down",
        "docker-compose ps",
        "docker-compose logs -f",
        "docker build -t",
        "docker run -d --name",
        "docker exec -it",
        "docker stop",
        "docker rm",
        "docker rmi",
        "docker system df",
        "docker system prune -a",
        "docker network ls",
        "docker volume ls",
        "docker inspect",
        "docker stats --no-stream",
        "docker top",
    ],
    "system": [
        "uname -a",
        "uptime",
        "free -h",
        "df -h",
        "top -bn1 | head -20",
        "ps aux --sort=-%mem | head -10",
        "ps aux --sort=-%cpu | head -10",
        "iostat -x 1 3",
        "vmstat 1 5",
        "sar -u 1 3",
        "lscpu",
        "lsblk",
        "cat /proc/meminfo",
        "cat /proc/cpuinfo",
        "hostnamectl",
        "journalctl -u",
        "systemctl status",
        "systemctl list-units --type=service",
        "dmesg | tail -50",
        "lsof -i :",
    ],
    "network": [
        "ifconfig",
        "ip addr show",
        "ip route show",
        "netstat -tlnp",
        "ss -tlnp",
        "ss -s",
        "curl -I",
        "wget --spider",
        "ping -c 4",
        "traceroute",
        "nslookup",
        "dig",
        "tcpdump -i eth0 -c 100",
        "nmap -sT -p",
        "iptables -L -n",
        "nc -zv",
        "arp -a",
        "route -n",
        "mtr --report",
        "ethtool",
    ],
    "file": [
        "ls -la",
        "ls -lhS",
        "ls -lhSr",
        "du -sh * | sort -rh | head -10",
        "find / -name",
        "find / -type f -size +100M",
        "find / -mtime -7 -type f",
        "grep -r",
        "wc -l",
        "tar -czf",
        "tar -xzf",
        "chmod -R",
        "chown -R",
        "ln -s",
        "tree -L 2",
        "fdisk -l",
        "mount",
        "df -i",
        "tail -f",
        "head -n 100",
    ],
    "process": [
        "ps aux",
        "ps -ef",
        "pgrep -f",
        "pkill -f",
        "kill -9",
        "kill -HUP",
        "nohup",
        "screen -ls",
        "screen -dmS",
        "tmux ls",
        "tmux new -s",
        "watch -n 1",
        "strace -p",
        "lsof -p",
        "nice -n",
        "renice",
        "atq",
        "crontab -l",
        "crontab -e",
        "/etc/init.d/",
    ],
    "security": [
        "last -n 20",
        "lastlog",
        "who",
        "w",
        "id",
        "passwd",
        "useradd",
        "userdel",
        "groups",
        "visudo",
        "ufw status",
        "fail2ban-client status",
        "cat /var/log/auth.log",
        "cat /var/log/secure",
        "openssl x509 -text -noout -in",
        "ssh-keygen -t rsa -b 4096",
        "ssh-copy-id",
        "chmod 600",
        "chattr +i",
        "getenforce",
    ],
    "deploy": [
        "nginx -t",
        "nginx -s reload",
        "supervisorctl status",
        "supervisorctl restart",
        "pm2 list",
        "pm2 restart",
        "pm2 logs",
        "kubectl get pods",
        "kubectl describe pod",
        "kubectl logs -f",
        "kubectl get svc",
        "kubectl get deployments",
        "kubectl apply -f",
        "helm list",
        "ansible-playbook",
        "rsync -avz",
        "scp -r",
        "git pull origin main",
        "git status",
        "make deploy",
    ],
}

NLP_COMMAND_MAP = {
    r"(cpu|CPU).*(占用|使用|最高|进程|process)": "ps aux --sort=-%cpu | head -10",
    r"(内存|memory|mem).*(占用|使用|最高|进程|process)": "ps aux --sort=-%mem | head -10",
    r"(磁盘|disk|硬盘).*(占用|使用|空间|剩余)": "df -h",
    r"(磁盘|disk|硬盘).*(大文件|占用高|最大)": "du -sh * | sort -rh | head -10",
    r"(网络|network|端口|port).*(监听|占用|listening)": "ss -tlnp",
    r"(网络|network|连接|connection)": "netstat -an | grep ESTABLISHED",
    r"(docker|容器|container).*(列表|list|所有)": "docker ps -a",
    r"(docker|容器|container).*(日志|log)": "docker logs --tail 100",
    r"(docker|容器|container).*(镜像|image)": "docker images",
    r"(docker|容器|container).*(进入|exec|shell)": "docker exec -it",
    r"(docker|容器|container).*(资源|占用|stats)": "docker stats --no-stream",
    r"(系统|system).*(信息|info|版本)": "uname -a",
    r"(系统|system).*(运行|uptime|时间)": "uptime",
    r"(系统|system).*(负载|load)": "uptime",
    r"(内存|memory|mem).*(信息|info|剩余|free)": "free -h",
    r"(进程|process).*(列表|list|所有)": "ps aux",
    r"(进程|process).*(杀|kill|停止|stop)": "kill -9",
    r"(服务|service).*(状态|status)": "systemctl status",
    r"(服务|service).*(重启|restart)": "systemctl restart",
    r"(服务|service).*(列表|list)": "systemctl list-units --type=service",
    r"(防火墙|firewall|ufw).*(状态|status)": "ufw status",
    r"(用户|user).*(登录|login|最近)": "last -n 20",
    r"(用户|user).*(当前|在线|online)": "who",
    r"(文件|file).*(查找|find|搜索|search)": "find / -name",
    r"(文件|file).*(大文件|最大的)": "find / -type f -size +100M",
    r"(nginx).*(测试|检查|config)": "nginx -t",
    r"(nginx).*(重启|reload)": "nginx -s reload",
    r"(k8s|kubernetes).*(pod|容器)": "kubectl get pods",
    r"(k8s|kubernetes).*(服务|service)": "kubectl get svc",
    r"(git).*(拉取|pull|更新)": "git pull origin main",
    r"(git).*(状态|status)": "git status",
    r"(日志|log).*(查看|实时|跟踪)": "tail -f",
    r"(定时|cron|crontab).*(任务|列表)": "crontab -l",
    r"(端口|port).*(开放|监听|listening)": "ss -tlnp",
    r"(连接|connect|连通|ping).*(测试|检查|test)": "ping -c 4",
    r"(ip).*(地址|address|查看)": "ip addr show",
}

CATEGORY_KEYWORDS = {
    "docker": ["docker", "container", "容器", "镜像", "image", "docker-compose", "compose"],
    "system": ["system", "系统", "cpu", "内存", "memory", "disk", "磁盘", "load", "负载", "uptime", "free", "df"],
    "network": ["network", "网络", "port", "端口", "ip", "curl", "ping", "netstat", "ss", "tcpdump", "route"],
    "file": ["file", "文件", "find", "查找", "ls", "chmod", "chown", "tar", "grep", "du", "tree"],
    "process": ["process", "进程", "ps", "kill", "pkill", "screen", "tmux", "nohup", "crontab", "watch"],
    "security": ["security", "安全", "firewall", "防火墙", "user", "用户", "ssh", "sudo", "ufw", "fail2ban"],
    "deploy": ["deploy", "部署", "nginx", "k8s", "kubernetes", "kubectl", "helm", "pm2", "supervisor", "git", "rsync", "ansible"],
}


class CommandHistoryEntry:
    __slots__ = ('command', 'timestamp', 'category', 'exit_code', 'count')

    def __init__(self, command: str, timestamp: str, category: str = "", exit_code: int = 0, count: int = 1):
        self.command = command
        self.timestamp = timestamp
        self.category = category
        self.exit_code = exit_code
        self.count = count

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "timestamp": self.timestamp,
            "category": self.category,
            "exit_code": self.exit_code,
            "count": self.count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CommandHistoryEntry':
        return cls(
            command=data.get("command", ""),
            timestamp=data.get("timestamp", ""),
            category=data.get("category", ""),
            exit_code=data.get("exit_code", 0),
            count=data.get("count", 1),
        )


class SuggestionEngine:
    def __init__(self):
        self._history: List[CommandHistoryEntry] = []
        self._feedback: List[dict] = []
        self._user_profile: Dict[str, float] = defaultdict(float)
        self._trie = CommandTrie()
        self._cache = LRUCache(max_size=512, ttl=60.0)
        self._lock = threading.RLock()
        self._command_freq: Dict[str, int] = defaultdict(int)
        self._category_freq: Dict[str, float] = defaultdict(float)
        self._negative_commands: Dict[str, int] = defaultdict(int)
        self._load_data()
        self._rebuild_index()

    def _load_data(self) -> None:
        for filepath, loader in [
            (HISTORY_FILE, self._load_history),
            (FEEDBACK_FILE, self._load_feedback),
            (USER_PROFILES_FILE, self._load_user_profiles),
        ]:
            if filepath.exists():
                try:
                    loader(filepath)
                except (json.JSONDecodeError, IOError):
                    pass

    def _load_history(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._history = [CommandHistoryEntry.from_dict(d) for d in data]

    def _load_feedback(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            self._feedback = json.load(f)
        for fb in self._feedback:
            if fb.get("useful") is False:
                self._negative_commands[fb.get("command", "")] += 1

    def _load_user_profiles(self, filepath: Path) -> None:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._user_profile = defaultdict(float, {k: float(v) for k, v in data.items()})

    def _save_data(self) -> None:
        for filepath, data, is_json in [
            (HISTORY_FILE, [e.to_dict() for e in self._history], True),
            (FEEDBACK_FILE, self._feedback, True),
            (USER_PROFILES_FILE, dict(self._user_profile), True),
        ]:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except IOError:
                pass

    def _rebuild_index(self) -> None:
        self._trie = CommandTrie()
        self._command_freq = defaultdict(int)
        self._category_freq = defaultdict(float)

        for entry in self._history:
            self._trie.insert(entry.command)
            self._command_freq[entry.command] += entry.count
            if entry.category:
                self._category_freq[entry.category] += entry.count

        for cat, commands in COMMAND_CATEGORIES.items():
            weight = self._user_profile.get(cat, 0.5)
            for cmd in commands:
                self._trie.insert(cmd)
                if cmd not in self._command_freq:
                    self._command_freq[cmd] = int(weight * 10)

    def record_command(self, command: str, exit_code: int = 0) -> None:
        if not command or not command.strip():
            return

        with self._lock:
            category = self._classify_command(command)
            now = datetime.now().isoformat()

            existing = None
            for entry in self._history:
                if entry.command == command:
                    existing = entry
                    break

            if existing:
                existing.count += 1
                existing.timestamp = now
                existing.exit_code = exit_code
            else:
                self._history.append(CommandHistoryEntry(
                    command=command,
                    timestamp=now,
                    category=category,
                    exit_code=exit_code,
                ))

            self._command_freq[command] += 1
            if category:
                self._category_freq[category] += 1
                self._user_profile[category] = min(self._user_profile[category] + 0.1, 5.0)

            self._trie.insert(command)
            self._cache.clear()
            self._save_data()

    def _classify_command(self, command: str) -> str:
        cmd_lower = command.lower().split()[0] if command.split() else ""
        for category, commands in COMMAND_CATEGORIES.items():
            for tmpl in commands:
                if tmpl.lower().startswith(cmd_lower):
                    return category
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in command.lower():
                    return category
        return "other"

    def get_suggestions(
        self,
        prefix: str,
        limit: int = 20,
        session_id: str = "default",
    ) -> List[dict]:
        cache_key = f"prefix:{prefix}:{limit}:{session_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        with self._lock:
            results = []

            trie_results = self._trie.search_prefix(prefix, limit=limit * 3)

            scored = []
            for cmd in trie_results:
                neg_count = self._negative_commands.get(cmd, 0)
                if neg_count >= 3:
                    continue

                freq = self._command_freq.get(cmd, 0)
                category = self._classify_command(cmd)
                cat_weight = self._user_profile.get(category, 0.5)

                is_history = any(e.command == cmd for e in self._history)
                history_bonus = 50 if is_history else 0

                recency_bonus = 0
                for e in self._history:
                    if e.command == cmd:
                        try:
                            ts = datetime.fromisoformat(e.timestamp)
                            hours_ago = (datetime.now() - ts).total_seconds() / 3600
                            recency_bonus = max(0, 30 - hours_ago * 0.5)
                        except (ValueError, TypeError):
                            pass
                        break

                neg_penalty = neg_count * 10

                score = freq * cat_weight + history_bonus + recency_bonus - neg_penalty
                scored.append((cmd, score, category, freq))

            scored.sort(key=lambda x: x[1], reverse=True)

            for cmd, score, category, freq in scored[:limit]:
                is_history = any(e.command == cmd for e in self._history)
                results.append({
                    "command": cmd,
                    "category": category,
                    "score": round(score, 2),
                    "frequency": freq,
                    "is_history": is_history,
                    "source": "history" if is_history else "template",
                })

            self._cache.put(cache_key, results)
            return results

    def get_collaborative_suggestions(self, limit: int = 10) -> List[dict]:
        with self._lock:
            top_categories = sorted(
                self._user_profile.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:3]

            if not top_categories:
                top_categories = [("system", 1.0), ("network", 0.8), ("docker", 0.6)]

            results = []
            seen = set()

            for category, weight in top_categories:
                commands = COMMAND_CATEGORIES.get(category, [])
                for cmd in commands:
                    if cmd in seen:
                        continue
                    seen.add(cmd)
                    freq = self._command_freq.get(cmd, 0)
                    is_history = any(e.command == cmd for e in self._history)
                    if not is_history:
                        results.append({
                            "command": cmd,
                            "category": category,
                            "score": round(weight * 10, 2),
                            "frequency": freq,
                            "is_history": False,
                            "source": "collaborative",
                        })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

    def natural_language_to_command(self, query: str) -> List[dict]:
        if not query or not query.strip():
            return []

        import re
        results = []
        seen_commands = set()

        for pattern, command in NLP_COMMAND_MAP.items():
            if re.search(pattern, query):
                if command not in seen_commands:
                    seen_commands.add(command)
                    category = self._classify_command(command)
                    cat_weight = self._user_profile.get(category, 0.5)
                    results.append({
                        "command": command,
                        "category": category,
                        "score": round(cat_weight * 20, 2),
                        "frequency": self._command_freq.get(command, 0),
                        "is_history": any(e.command == command for e in self._history),
                        "source": "nlp",
                        "matched_pattern": pattern,
                    })

        query_tokens = query.lower().split()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in query_tokens:
                    commands = COMMAND_CATEGORIES.get(category, [])
                    for cmd in commands[:3]:
                        if cmd not in seen_commands:
                            seen_commands.add(cmd)
                            results.append({
                                "command": cmd,
                                "category": category,
                                "score": round(self._user_profile.get(category, 0.5) * 5, 2),
                                "frequency": self._command_freq.get(cmd, 0),
                                "is_history": any(e.command == cmd for e in self._history),
                                "source": "nlp_keyword",
                            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:10]

    def submit_feedback(self, command: str, useful: bool, reason: str = "") -> None:
        with self._lock:
            entry = {
                "command": command,
                "useful": useful,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
            self._feedback.append(entry)

            if not useful:
                self._negative_commands[command] += 1
                category = self._classify_command(command)
                if category:
                    self._user_profile[category] = max(self._user_profile[category] - 0.05, 0.1)
            else:
                category = self._classify_command(command)
                if category:
                    self._user_profile[category] = min(self._user_profile[category] + 0.02, 5.0)

            self._cache.clear()
            self._save_data()

    def get_history(self, limit: int = 50, category: str = "") -> List[dict]:
        with self._lock:
            entries = self._history
            if category:
                entries = [e for e in entries if e.category == category]
            sorted_entries = sorted(entries, key=lambda x: x.timestamp, reverse=True)
            return [e.to_dict() for e in sorted_entries[:limit]]

    def get_user_profile(self) -> dict:
        with self._lock:
            return {
                "category_weights": dict(self._user_profile),
                "top_categories": sorted(
                    self._user_profile.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5],
                "total_commands": len(self._history),
                "total_feedback": len(self._feedback),
                "negative_commands_count": len(self._negative_commands),
            }


suggestion_engine = SuggestionEngine()
