"""
World Book Plugin for KiraAI
=============================
根据对话中的关键词自动将世界书条目注入 LLM 上下文。

v1.1 修复：
  - 仅扫描用户消息，不扫描 AI 回复，避免循环触发
  - 支持条目级别 scan_depth，带缓存
  - 二级关键词仅基于用户文本 + 已激活条目内容匹配
  - 改进日志，显示匹配原因
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from core.plugin import BasePlugin, logger, register_tool, on, Priority
from core.prompt_manager import Prompt


# ──────────────────────────────────────────────
#  Data Model
# ──────────────────────────────────────────────

@dataclass
class WorldBookEntry:
    """单个世界书条目"""

    # ── 基本信息 ──
    name: str = "unnamed"
    keywords: List[str] = field(default_factory=list)
    content: str = ""
    enabled: bool = True
    comment: str = ""

    # ── 触发控制 ──
    constant: bool = False
    scan_depth: Optional[int] = None
    case_sensitive: bool = False
    match_whole_words: bool = False
    use_regex: bool = False

    # ── 二级关键词 ──
    secondary_keywords: List[str] = field(default_factory=list)
    exclude_recursion: bool = False

    # ── 注入控制 ──
    position: str = "system_note"
    insertion_order: int = 100
    priority: int = 50

    # ── 分组 ──
    group: str = ""
    group_weight: int = 100

    # ── 元数据 ──
    source_file: str = ""


# ──────────────────────────────────────────────
#  Plugin
# ──────────────────────────────────────────────

class WorldBookPlugin(BasePlugin):

    def __init__(self, ctx, cfg: dict):
        super().__init__(ctx, cfg)
        self.entries: List[WorldBookEntry] = []
        self.books: Dict[str, List[WorldBookEntry]] = {}
        self.data_dir: Optional[Path] = None

    # ============================================================
    #  Lifecycle
    # ============================================================

    async def initialize(self):
        self.data_dir = self.ctx.get_plugin_data_dir()
        if self.data_dir is None:
            logger.error("[WorldBook] 无法获取插件数据目录")
            return

        books_dir = self.data_dir / "books"
        books_dir.mkdir(parents=True, exist_ok=True)

        if not self._find_book_files(books_dir):
            self._create_example_book(books_dir)

        self._load_all_books()

        enabled = sum(1 for e in self.entries if e.enabled)
        logger.info(
            f"[WorldBook] 已加载 {len(self.entries)} 个条目"
            f"（{enabled} 个启用），来自 {len(self.books)} 本世界书"
        )
        if not HAS_YAML:
            logger.warning(
                "[WorldBook] 未安装 PyYAML，仅支持 JSON 格式。"
                "安装命令：pip install pyyaml"
            )

    async def terminate(self):
        self.entries.clear()
        self.books.clear()
        logger.info("[WorldBook] 插件已终止")

    # ============================================================
    #  File I/O
    # ============================================================

    @staticmethod
    def _find_book_files(directory: Path) -> List[Path]:
        files: List[Path] = []
        for pattern in ("*.yaml", "*.yml", "*.json"):
            files.extend(directory.glob(pattern))
        return sorted(files)

    def _create_example_book(self, books_dir: Path):
        data = {
            "book_name": "示例世界书",
            "description": "修改此文件或在 books/ 目录下创建新的 .yaml / .json 文件",
            "entries": [
                {
                    "name": "示例 - 常驻条目",
                    "keywords": [],
                    "content": (
                        "常驻条目始终注入上下文，无需关键词触发。\n"
                        "将 enabled 改为 true 来启用此条目。"
                    ),
                    "enabled": False,
                    "constant": True,
                    "position": "system_note",
                    "insertion_order": 100,
                    "priority": 50,
                    "comment": "默认禁用的常驻示例",
                },
                {
                    "name": "示例 - 关键词触发",
                    "keywords": ["魔法", "magic", "法术"],
                    "content": (
                        "当对话中出现任一关键词时，此条目自动注入。\n"
                        "支持多个关键词，任意一个匹配即触发。"
                    ),
                    "enabled": False,
                    "constant": False,
                    "position": "system_note",
                    "insertion_order": 200,
                    "priority": 50,
                    "scan_depth": 10,
                    "case_sensitive": False,
                    "match_whole_words": False,
                    "use_regex": False,
                    "comment": "关键词触发示例",
                },
                {
                    "name": "示例 - 正则匹配",
                    "keywords": ["\\b\\d{4}年\\b"],
                    "content": "当对话中出现「XXXX年」格式时触发。",
                    "enabled": False,
                    "use_regex": True,
                    "position": "system_note",
                    "insertion_order": 300,
                    "priority": 30,
                    "comment": "正则匹配示例",
                },
                {
                    "name": "示例 - 二级关键词",
                    "keywords": [],
                    "secondary_keywords": ["魔法"],
                    "content": (
                        "当其他已激活条目的内容中包含二级关键词时，\n"
                        "此条目也会被连带激活。\n"
                        "注意：二级关键词也会扫描用户的对话内容。"
                    ),
                    "enabled": False,
                    "position": "system_note",
                    "insertion_order": 400,
                    "priority": 20,
                    "comment": "二级关键词递归激活示例",
                },
            ],
        }

        if HAS_YAML:
            path = books_dir / "example.yaml"
            try:
                with path.open("w", encoding="utf-8") as f:
                    yaml.dump(
                        data, f,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                        width=120,
                    )
                logger.info(f"[WorldBook] 已创建示例文件：{path}")
            except Exception as e:
                logger.error(f"[WorldBook] 创建示例失败：{e}")
        else:
            path = books_dir / "example.json"
            try:
                with path.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"[WorldBook] 已创建示例文件：{path}")
            except Exception as e:
                logger.error(f"[WorldBook] 创建示例失败：{e}")

    def _load_all_books(self):
        self.entries.clear()
        self.books.clear()

        books_dir = self.data_dir / "books"
        if not books_dir.exists():
            return

        for fp in self._find_book_files(books_dir):
            try:
                self._load_book_file(fp)
            except Exception as e:
                logger.error(f"[WorldBook] 加载 '{fp.name}' 失败：{e}")

    def _load_book_file(self, file_path: Path):
        suffix = file_path.suffix.lower()
        with file_path.open("r", encoding="utf-8") as f:
            if suffix in (".yaml", ".yml"):
                if not HAS_YAML:
                    logger.warning(f"[WorldBook] 跳过 '{file_path.name}'：未安装 PyYAML")
                    return
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        if not isinstance(data, dict):
            return

        book_name = data.get("book_name", file_path.stem)
        raw_list = data.get("entries", [])
        if not isinstance(raw_list, list):
            return

        book_entries: List[WorldBookEntry] = []
        for idx, raw in enumerate(raw_list):
            if not isinstance(raw, dict):
                continue
            try:
                entry = self._parse_entry(raw, idx, file_path.name)
                book_entries.append(entry)
            except Exception as e:
                logger.warning(f"[WorldBook] '{book_name}' 条目 #{idx} 解析失败：{e}")

        self.books[book_name] = book_entries
        self.entries.extend(book_entries)

    def _parse_entry(self, raw: dict, idx: int, source: str) -> WorldBookEntry:
        return WorldBookEntry(
            name=str(raw.get("name", f"entry_{idx}")),
            keywords=self._to_str_list(raw.get("keywords", [])),
            content=str(raw.get("content", "")),
            enabled=bool(raw.get("enabled", True)),
            comment=str(raw.get("comment", "")),
            constant=bool(raw.get("constant", False)),
            scan_depth=raw.get("scan_depth"),
            case_sensitive=bool(raw.get("case_sensitive", False)),
            match_whole_words=bool(raw.get("match_whole_words", False)),
            use_regex=bool(raw.get("use_regex", False)),
            secondary_keywords=self._to_str_list(raw.get("secondary_keywords", [])),
            exclude_recursion=bool(raw.get("exclude_recursion", False)),
            position=str(raw.get("position", "system_note")),
            insertion_order=int(raw.get("insertion_order", 100)),
            priority=int(raw.get("priority", 50)),
            group=str(raw.get("group", "")),
            group_weight=int(raw.get("group_weight", 100)),
            source_file=source,
        )

    @staticmethod
    def _to_str_list(value) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value if v]
        if isinstance(value, str) and value:
            return [value]
        return []

    # ============================================================
    #  Keyword Matching  (无变化)
    # ============================================================

    @staticmethod
    def _match_keywords(
        text: str,
        keywords: List[str],
        case_sensitive: bool = False,
        match_whole_words: bool = False,
        use_regex: bool = False,
    ) -> bool:
        for kw in keywords:
            if not kw:
                continue
            try:
                if use_regex:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    if re.search(kw, text, flags):
                        return True
                else:
                    t = text if case_sensitive else text.lower()
                    k = kw if case_sensitive else kw.lower()
                    if match_whole_words:
                        if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", t):
                            return True
                    else:
                        if k in t:
                            return True
            except re.error:
                t = text if case_sensitive else text.lower()
                k = kw if case_sensitive else kw.lower()
                if k in t:
                    return True
        return False

    # ============================================================
    #  ★ 修复核心：文本提取与扫描
    # ============================================================

    @staticmethod
    def _extract_message_content(msg) -> str:
        """从消息字典中提取文本内容，兼容字符串和多模态列表格式"""
        if not isinstance(msg, dict):
            return ""
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    parts.append(part)
            return "\n".join(parts)
        return ""

    def _extract_user_texts(
        self, messages: list, user_prompts: list
    ) -> List[str]:
        """
        ★ 关键修复：仅提取 role=user 的消息文本。
        
        排除 assistant / system / tool 消息，避免 AI 回复中的
        世界书内容造成下一轮循环触发。
        """
        texts: List[str] = []

        # ── 历史消息：仅取 role=user ──
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = self._extract_message_content(msg)
                if content.strip():
                    texts.append(content)

        # ── 当前用户输入 ──
        for p in user_prompts:
            if hasattr(p, "content") and isinstance(p.content, str):
                if p.content.strip():
                    texts.append(p.content)
            elif isinstance(p, dict):
                content = self._extract_message_content(p)
                if content.strip():
                    texts.append(content)
            elif isinstance(p, str) and p.strip():
                texts.append(p)

        return texts

    @staticmethod
    def _join_recent(texts: List[str], depth: int) -> str:
        """取最近 depth 条文本拼接"""
        recent = texts[-depth:] if len(texts) > depth else texts
        return "\n".join(recent)

    # ============================================================
    #  ★ 修复核心：条目收集
    # ============================================================

    def _collect_matches(
        self, user_texts: List[str], default_depth: int
    ) -> List[WorldBookEntry]:
        """
        两轮匹配，支持条目级别 scan_depth。
        
        ★ 修复：
          - 仅扫描用户消息，不包含 AI 回复
          - 按条目各自的 scan_depth 构建扫描文本（带缓存）
        """
        matched: List[WorldBookEntry] = []
        match_reasons: Dict[str, str] = {}  # name → reason (调试用)
        seen: Set[int] = set()

        # 扫描文本缓存：depth → text
        scan_cache: Dict[int, str] = {}

        def get_scan(depth: int) -> str:
            if depth not in scan_cache:
                scan_cache[depth] = self._join_recent(user_texts, depth)
            return scan_cache[depth]

        # ── 第一轮：常驻 + 关键词直接匹配 ──
        for entry in self.entries:
            if not entry.enabled or not entry.content:
                continue

            if entry.constant:
                if id(entry) not in seen:
                    matched.append(entry)
                    seen.add(id(entry))
                    match_reasons[entry.name] = "constant"
                continue

            if not entry.keywords:
                continue

            depth = entry.scan_depth if entry.scan_depth is not None else default_depth
            scan_text = get_scan(depth)

            if not scan_text:
                continue

            if self._match_keywords(
                scan_text,
                entry.keywords,
                entry.case_sensitive,
                entry.match_whole_words,
                entry.use_regex,
            ):
                if id(entry) not in seen:
                    matched.append(entry)
                    seen.add(id(entry))
                    match_reasons[entry.name] = f"keyword(depth={depth})"

        # ── 第二轮：二级关键词递归 ──
        if matched:
            activated_content = "\n".join(e.content for e in matched)
            full_user_text = get_scan(default_depth)
            combined = full_user_text + "\n" + activated_content

            for entry in self.entries:
                if not entry.enabled or not entry.content:
                    continue
                if id(entry) in seen or entry.exclude_recursion:
                    continue
                if not entry.secondary_keywords:
                    continue
                if self._match_keywords(
                    combined,
                    entry.secondary_keywords,
                    entry.case_sensitive,
                    entry.match_whole_words,
                    entry.use_regex,
                ):
                    matched.append(entry)
                    seen.add(id(entry))
                    match_reasons[entry.name] = "secondary_keyword"

        # 日志：显示匹配原因
        if match_reasons:
            reasons_str = ", ".join(
                f"{name}({reason})" for name, reason in match_reasons.items()
            )
            logger.debug(f"[WorldBook] 匹配详情：{reasons_str}")

        return matched

    # ============================================================
    #  Budget & Limits  (基本无变化)
    # ============================================================

    def _apply_limits(self, entries: List[WorldBookEntry]) -> List[WorldBookEntry]:
        max_per_group = int(self.plugin_cfg.get("max_entries_per_group", 10))

        groups: Dict[str, List[WorldBookEntry]] = {}
        ungrouped: List[WorldBookEntry] = []
        for e in entries:
            if e.group:
                groups.setdefault(e.group, []).append(e)
            else:
                ungrouped.append(e)

        result = list(ungrouped)
        for g_entries in groups.values():
            g_entries.sort(key=lambda x: -x.group_weight)
            result.extend(g_entries[:max_per_group])

        result.sort(key=lambda e: (-e.priority, e.insertion_order))

        cap = int(self.plugin_cfg.get("max_entries", 20))
        if cap > 0 and len(result) > cap:
            result = result[:cap]

        return result

    def _apply_char_budget(self, entries: List[WorldBookEntry]) -> List[WorldBookEntry]:
        max_chars = int(self.plugin_cfg.get("max_chars", 16000))
        if max_chars <= 0:
            return entries

        total = 0
        kept: List[WorldBookEntry] = []
        for e in entries:
            cost = len(e.name) + len(e.content) + 10
            if total + cost > max_chars:
                logger.debug(f"[WorldBook] 字符预算用尽，跳过剩余条目")
                break
            kept.append(e)
            total += cost
        return kept

    # ============================================================
    #  LLM Request Hook — 核心注入
    # ============================================================

    @on.llm_request(priority=Priority.HIGH)
    async def inject_world_book(self, event, request, tag_set):
        """ON_LLM_REQUEST：扫描用户对话并注入匹配的世界书条目"""
        if not self.entries:
            return

        default_depth = int(self.plugin_cfg.get("scan_depth", 50))

        # ★ 修复：仅提取用户消息，不含 AI 回复
        user_texts = self._extract_user_texts(
            request.messages, request.user_prompt
        )
        if not user_texts:
            return

        # ★ 修复：传入用户文本列表，支持条目级 scan_depth
        matched = self._collect_matches(user_texts, default_depth)
        if not matched:
            return

        matched = self._apply_limits(matched)
        matched = self._apply_char_budget(matched)
        if not matched:
            return

        # 按 position 分组
        by_pos: Dict[str, List[str]] = {}
        for e in matched:
            pos = (
                e.position
                if e.position in ("system_note", "before_persona", "after_persona")
                else "system_note"
            )
            by_pos.setdefault(pos, []).append(f"【{e.name}】\n{e.content}")

        header = self.plugin_cfg.get(
            "injection_header",
            "[World Book / 世界书 - 背景设定与参考知识]",
        )

        for pos, parts in by_pos.items():
            combined = f"{header}\n" + "\n\n".join(parts)
            prompt = Prompt(
                combined, name=f"world_book_{pos}", source="plugin"
            )

            if pos == "before_persona":
                idx = self._find_persona_idx(request.system_prompt)
                request.system_prompt.insert(idx, prompt)
            elif pos == "after_persona":
                idx = self._find_persona_idx(request.system_prompt) + 1
                idx = min(idx, len(request.system_prompt))
                request.system_prompt.insert(idx, prompt)
            else:
                request.system_prompt.append(prompt)

        names = [e.name for e in matched]
        logger.info(f"[WorldBook] 已注入 {len(matched)} 个条目：{names}")

    @staticmethod
    def _find_persona_idx(prompts: list) -> int:
        for i, p in enumerate(prompts):
            if hasattr(p, "name") and p.name in (
                "character", "persona", "char",
            ):
                return i
        return 0

    # ============================================================
    #  Search
    # ============================================================

    def _search(
        self, query: str, include_disabled: bool = False
    ) -> List[WorldBookEntry]:
        q = query.lower()
        hits: List[WorldBookEntry] = []
        for e in self.entries:
            if not include_disabled and not e.enabled:
                continue
            if q in e.name.lower():
                hits.append(e)
                continue
            if any(q in k.lower() for k in e.keywords):
                hits.append(e)
                continue
            if q in e.content.lower():
                hits.append(e)
        return hits

    # ============================================================
    #  Tool Functions
    # ============================================================

    @register_tool(
        name="world_book_search",
        description="在世界书（知识库）中搜索条目。查找设定、背景信息或世界观知识时使用。",
        params={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或短语",
                }
            },
            "required": ["query"],
        },
    )
    async def world_book_search(self, event, query: str) -> str:
        results = self._search(query)
        if not results:
            return f"未找到与「{query}」相关的世界书条目。"

        lines = [f"【{e.name}】\n{e.content}" for e in results[:10]]
        head = f"找到 {len(results)} 个相关条目"
        if len(results) > 10:
            head += "（显示前 10 个）"
        return head + ":\n\n" + "\n---\n".join(lines)

    @register_tool(
        name="world_book_reload",
        description="重新加载所有世界书文件（文件修改后调用以刷新）。",
        params={
            "type": "object",
            "properties": {},
        },
    )
    async def world_book_reload(self, event) -> str:
        try:
            self._load_all_books()
            enabled = sum(1 for e in self.entries if e.enabled)
            return (
                f"世界书已重新加载：{len(self.entries)} 个条目"
                f"（{enabled} 个启用），{len(self.books)} 本书。"
            )
        except Exception as e:
            return f"世界书重新加载失败：{e}"