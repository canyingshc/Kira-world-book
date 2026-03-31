# 📖 World Book Plugin for KiraAI

> 世界书知识管理插件 — 根据对话关键词自动注入背景设定与知识到 LLM 上下文中。

[![Plugin Version](https://img.shields.io/badge/version-1.1.0-blue)]()
[![KiraAI](https://img.shields.io/badge/platform-KiraAI-purple)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## ✨ 功能特性

- **关键词触发** — 用户对话中出现指定关键词时，自动将对应设定注入 LLM 上下文
- **常驻条目** — 无需关键词，每次对话始终注入
- **正则匹配** — 支持正则表达式作为触发条件
- **全词匹配** — 可选仅匹配完整单词，避免误触发
- **二级关键词** — 已激活条目的内容可递归触发其他条目
- **多注入位置** — `system_note` / `before_persona` / `after_persona` 三种插入点
- **分组与预算** — 按分组限制条目数，按字符总量裁剪，防止上下文溢出
- **YAML + JSON 双格式** — 推荐使用 YAML，可读性更强；不装 PyYAML 也可用 JSON
- **多文件世界书** — `books/` 目录下每个文件是一本独立的世界书，互不干扰
- **工具函数** — LLM 可主动调用 `world_book_search` 查询知识、`world_book_reload` 热重载
- **仅扫描用户消息** — 不扫描 AI 回复，从根本上杜绝循环注入问题

---

## 📁 目录结构

```text
data/plugins/world_book/          ← 插件安装目录
├── manifest.json                  ← 插件元数据
├── schema.json                    ← 配置界面定义
├── main.py                        ← 主插件逻辑
└── README.md
data/plugin_data/world_book/     ← 运行时自动生成
└── books/
    ├── example.yaml               ← 自动创建的示例（首次启动）
    ├── my_fantasy_world.yaml      ← 你的世界书（自行创建）
    └── characters.json            ← 也支持 JSON 格式
```

---

## 🚀 安装

### 1. 放置插件

将整个 `world_book` 文件夹复制到 `data/plugins/` 目录下。

### 2. 安装依赖（推荐）

```bash
pip install pyyaml httpx
```

> 不安装 PyYAML 也能运行，但只支持 JSON 格式的世界书文件。

### 3. 启动 / 重启 KiraAI

插件会自动被发现和加载。首次启动时会在 `data/plugin_data/world_book/books/` 中创建示例文件。

---

## 📝 编写世界书

在 `data/plugin_data/world_book/books/` 目录下创建 `.yaml` 或 `.json` 文件。

### YAML 格式（推荐）

```yaml
book_name: "我的奇幻世界"
description: "世界观核心设定"

entries:
  # ── 常驻条目：始终注入，无需关键词 ──
  - name: "世界观概述"
    content: |
      这是一个剑与魔法的奇幻世界。
      大陆名为「艾尔迪亚」，分为五大王国。
    enabled: true
    constant: true
    position: "before_persona"
    insertion_order: 10
    priority: 100

  # ── 关键词触发 ──
  - name: "火焰魔法"
    keywords:
      - "火焰"
      - "火球"
      - "烈焰"
    content: |
      火焰魔法是最常见的攻击型魔法之一。
      初级法术：火球术
      中级法术：烈焰风暴
      高级法术：陨石坠落
    enabled: true
    scan_depth: 20

  # ── 正则匹配 ──
  - name: "历史纪年"
    keywords:
      - "第[一二三四五六七八九十百千]+纪"
      - "\\d+年前"
    content: |
      第一纪：创世纪（神明降临）
      第二纪：魔法纪（魔法文明鼎盛）
      第三纪：战争纪（五国争霸）
      第四纪：当前，和平纪
    enabled: true
    use_regex: true

  # ── 二级关键词递归 ──
  - name: "以太详解"
    keywords: []
    secondary_keywords:
      - "以太"
    content: "以太是弥漫在世界中的神秘能量……"
    enabled: true

  # ── 带分组的条目 ──
  - name: "王国：阿斯塔"
    keywords: ["阿斯塔"]
    content: "阿斯塔王国位于大陆北方，以骑士团闻名。"
    group: "kingdoms"
    group_weight: 100

  - name: "王国：艾伦"
    keywords: ["艾伦"]
    content: "艾伦王国位于大陆东方，是最大的商业国家。"
    group: "kingdoms"
    group_weight: 90
```

### JSON 格式

<details>
<summary>点击展开 JSON 模板</summary>

```json
{
  "book_name": "我的奇幻世界",
  "description": "世界观核心设定",
  "entries": [
    {
      "name": "世界观概述",
      "keywords": [],
      "content": "这是一个剑与魔法的奇幻世界。\n大陆名为「艾尔迪亚」，分为五大王国。",
      "enabled": true,
      "constant": true,
      "position": "before_persona",
      "insertion_order": 10,
      "priority": 100,
      "comment": "常驻条目，始终注入"
    },
    {
      "name": "火焰魔法",
      "keywords": ["火焰", "火球", "烈焰"],
      "content": "火焰魔法是最常见的攻击型魔法之一。\n初级法术：火球术\n中级法术：烈焰风暴\n高级法术：陨石坠落",
      "enabled": true,
      "constant": false,
      "scan_depth": 20,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "position": "system_note",
      "insertion_order": 100,
      "priority": 50,
      "comment": "关键词触发示例"
    },
    {
      "name": "历史纪年",
      "keywords": ["第[一二三四五六七八九十百千]+纪", "\\d+年前"],
      "content": "第一纪：创世纪（神明降临）\n第二纪：魔法纪（魔法文明鼎盛）\n第三纪：战争纪（五国争霸）\n第四纪：当前，和平纪",
      "enabled": true,
      "use_regex": true,
      "position": "system_note",
      "insertion_order": 150,
      "priority": 40,
      "comment": "正则匹配示例"
    },
    {
      "name": "以太详解",
      "keywords": [],
      "secondary_keywords": ["以太"],
      "content": "以太是弥漫在世界中的神秘能量……",
      "enabled": true,
      "position": "system_note",
      "insertion_order": 200,
      "priority": 30,
      "comment": "二级关键词递归激活示例"
    },
    {
      "name": "王国：阿斯塔",
      "keywords": ["阿斯塔"],
      "content": "阿斯塔王国位于大陆北方，以骑士团闻名。",
      "enabled": true,
      "group": "kingdoms",
      "group_weight": 100,
      "position": "system_note",
      "insertion_order": 300,
      "priority": 50,
      "comment": "分组示例"
    },
    {
      "name": "王国：艾伦",
      "keywords": ["艾伦"],
      "content": "艾伦王国位于大陆东方，是最大的商业国家。",
      "enabled": true,
      "group": "kingdoms",
      "group_weight": 90,
      "position": "system_note",
      "insertion_order": 310,
      "priority": 50,
      "comment": "分组示例"
    }
  ]
}
```

</details>

---

## 📋 条目字段参考

### 基本信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | `"unnamed"` | 条目名称，会显示在注入标题中 |
| `keywords` | list\<string\> | `[]` | 触发关键词，任一匹配即激活 |
| `content` | string | `""` | 注入到 LLM 上下文的正文内容 |
| `enabled` | bool | `true` | 是否启用此条目 |
| `comment` | string | `""` | 备注说明，不会被注入 |

### 触发控制

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `constant` | bool | `false` | 常驻模式，始终注入无需关键词 |
| `scan_depth` | int \| null | `null` | 向前扫描几条用户消息；`null` = 使用全局配置 |
| `case_sensitive` | bool | `false` | 关键词是否区分大小写 |
| `match_whole_words` | bool | `false` | 是否全词匹配（避免部分匹配） |
| `use_regex` | bool | `false` | 是否将关键词视为正则表达式 |

### 二级关键词

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `secondary_keywords` | list\<string\> | `[]` | 当用户文本或已激活条目内容中出现这些词时，此条目也被激活 |
| `exclude_recursion` | bool | `false` | 设为 `true` 则此条目不会被二级关键词激活 |

### 注入控制

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `position` | string | `"system_note"` | 注入位置，见下方说明 |
| `insertion_order` | int | `100` | 同位置内的排列顺序（升序，越小越靠前） |
| `priority` | int | `50` | 选择优先级（降序，预算不足时优先保留） |

### 分组

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `group` | string | `""` | 分组名称，同组受 `max_entries_per_group` 限制 |
| `group_weight` | int | `100` | 组内权重（降序，优先保留高权重条目） |

---

## 📍 注入位置说明

```
┌─────────────────────────────────────────┐
│  system_prompt                          │
│  ┌───────────────────────────────────┐  │
│  │  ... other system prompts ...     │  │
│  ├───────────────────────────────────┤  │
│  │  ★ before_persona 注入点          │  │
│  ├───────────────────────────────────┤  │
│  │  🎭 Persona / Character prompt    │  │
│  ├───────────────────────────────────┤  │
│  │  ★ after_persona 注入点           │  │
│  ├───────────────────────────────────┤  │
│  │  ... other system prompts ...     │  │
│  ├───────────────────────────────────┤  │
│  │  ★ system_note 注入点（末尾追加） │  │
│  └───────────────────────────────────┘  │
│  user_prompt                            │
│  assistant response                     │
└─────────────────────────────────────────┘
```

| 位置 | 适用场景 |
|------|----------|
| `system_note` | 大多数知识条目（默认） |
| `before_persona` | 世界观基础设定，需要在角色设定之前建立背景 |
| `after_persona` | 与角色直接相关的补充设定 |

---

## ⚙️ 插件配置

通过 KiraAI 管理界面修改，或直接编辑 `config/plugins/world_book.json`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `scan_depth` | `50` | 全局默认扫描深度（条目可单独覆盖） |
| `max_entries` | `20` | 单次请求最多注入多少个条目（`0` = 无限制） |
| `max_entries_per_group` | `10` | 每个分组内最多激活多少个条目 |
| `max_chars` | `16000` | 注入内容总字符数上限（`0` = 无限制） |
| `injection_header` | `[World Book / 世界书 ...]` | 注入内容的标题文本 |

---

## 🛠️ 工具函数

LLM 可在对话中主动调用以下工具：

### `world_book_search`

在世界书中搜索条目，匹配名称、关键词和内容。

```
参数：query (string) — 搜索关键词
返回：匹配的条目列表（最多 10 条）
```

### `world_book_reload`

重新加载 `books/` 目录下的所有世界书文件。修改文件后无需重启，调用此工具即可生效。

```
参数：无
返回：加载结果统计
```

---

## 💡 最佳实践

### 避免循环注入

本插件**仅扫描用户消息**，不扫描 AI 回复，从设计上杜绝了循环触发问题。

### 常驻条目 + 二级关键词

注意：常驻条目的**内容**会参与二级关键词匹配。如果常驻条目内容中包含某个二级关键词，该条目会**每轮**被激活。

```yaml
# 如果不想要这种行为：

# 方案 1：排除递归
- name: "以太详解"
  exclude_recursion: true       # ← 不被二级关键词触发

# 方案 2：改用直接关键词
- name: "以太详解"
  keywords: ["以太"]             # ← 仅用户提到时才触发
  secondary_keywords: []
```

### 合理设置 scan_depth

- **全局默认 50** 通常够用
- 高频触发的通用词，建议设小（如 `scan_depth: 5`），只匹配最近几条
- 罕见的专有名词，可设大或使用默认值

### 善用分组

同类条目（如各个国家、各种魔法流派）放入同一分组，用 `max_entries_per_group` 控制激活上限，避免大量相关条目同时注入占满预算。

### 文件组织建议

```
books/
├── world_base.yaml       # 世界观基础（常驻条目为主）
├── magic_system.yaml     # 魔法体系
├── characters.yaml       # NPC 设定
├── locations.yaml        # 地点设定
└── history.yaml          # 历史事件
```

---

## ❓ 常见问题

<details>
<summary><b>Q: 修改了 YAML 文件后需要重启吗？</b></summary>

不需要。让 LLM 调用 `world_book_reload` 工具即可热重载，或在管理界面重载插件。

</details>

<details>
<summary><b>Q: 支持多少个世界书文件？</b></summary>

无数量限制。`books/` 目录下所有 `.yaml` / `.yml` / `.json` 文件都会被加载。

</details>

<details>
<summary><b>Q: 条目太多会不会拖慢速度？</b></summary>

关键词匹配是纯文本操作，数百个条目基本无感知。真正影响速度的是注入到 LLM 的文本量，通过 `max_chars` 和 `max_entries` 控制即可。

</details>

<details>
<summary><b>Q: 不安装 PyYAML 能用吗？</b></summary>

可以，但只支持 JSON 格式。插件启动时会提示警告，YAML 文件会被跳过。

</details>

<details>
<summary><b>Q: 如何确认哪些条目被注入了？</b></summary>

查看日志中 `[WorldBook] 已注入 X 个条目：[...]` 的输出。开启 DEBUG 级别可看到每个条目的匹配原因。

</details>

---

## example.json（JSON 模板）

放置路径：`data/plugin_data/world_book/books/example.json`

```json
{
  "book_name": "示例世界书",
  "description": "修改此文件或在 books/ 目录下创建新的 .yaml / .json 文件",
  "entries": [
    {
      "name": "示例 - 常驻条目",
      "keywords": [],
      "content": "常驻条目始终注入上下文，无需关键词触发。\n将 enabled 改为 true 来启用此条目。",
      "enabled": false,
      "constant": true,
      "scan_depth": null,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "secondary_keywords": [],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 100,
      "priority": 50,
      "group": "",
      "group_weight": 100,
      "comment": "默认禁用的常驻示例"
    },
    {
      "name": "示例 - 关键词触发",
      "keywords": [
        "魔法",
        "magic",
        "法术"
      ],
      "content": "当对话中出现任一关键词时，此条目自动注入。\n支持多个关键词，任意一个匹配即触发。",
      "enabled": false,
      "constant": false,
      "scan_depth": 10,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "secondary_keywords": [],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 200,
      "priority": 50,
      "group": "",
      "group_weight": 100,
      "comment": "关键词触发示例"
    },
    {
      "name": "示例 - 正则匹配",
      "keywords": [
        "\\b\\d{4}年\\b"
      ],
      "content": "当对话中出现「XXXX年」格式时触发。",
      "enabled": false,
      "constant": false,
      "scan_depth": null,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": true,
      "secondary_keywords": [],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 300,
      "priority": 30,
      "group": "",
      "group_weight": 100,
      "comment": "正则匹配示例"
    },
    {
      "name": "示例 - 二级关键词",
      "keywords": [],
      "content": "当其他已激活条目的内容中包含二级关键词时，\n此条目也会被连带激活。\n注意：二级关键词也会扫描用户的对话内容。",
      "enabled": false,
      "constant": false,
      "scan_depth": null,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "secondary_keywords": [
        "魔法"
      ],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 400,
      "priority": 20,
      "group": "",
      "group_weight": 100,
      "comment": "二级关键词递归激活示例"
    },
    {
      "name": "示例 - 分组条目 A",
      "keywords": [
        "阿斯塔",
        "阿斯塔王国"
      ],
      "content": "阿斯塔王国位于大陆北方，以骑士团闻名。国王为铁壁之王·雷昂哈特。",
      "enabled": false,
      "constant": false,
      "scan_depth": null,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "secondary_keywords": [],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 500,
      "priority": 50,
      "group": "kingdoms",
      "group_weight": 100,
      "comment": "分组示例 - 同组条目受 max_entries_per_group 限制"
    },
    {
      "name": "示例 - 分组条目 B",
      "keywords": [
        "艾伦",
        "艾伦王国"
      ],
      "content": "艾伦王国位于大陆东方，是最大的商业国家。以贸易和航海闻名。",
      "enabled": false,
      "constant": false,
      "scan_depth": null,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "secondary_keywords": [],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 510,
      "priority": 50,
      "group": "kingdoms",
      "group_weight": 90,
      "comment": "分组示例 - group_weight 越大在组内越优先保留"
    }
  ]
}
```

---

## 空白模板（JSON）

快速创建新世界书时复制使用：

```json
{
  "book_name": "新世界书",
  "description": "",
  "entries": [
    {
      "name": "条目名称",
      "keywords": ["关键词1", "关键词2"],
      "content": "条目内容",
      "enabled": true,
      "constant": false,
      "scan_depth": null,
      "case_sensitive": false,
      "match_whole_words": false,
      "use_regex": false,
      "secondary_keywords": [],
      "exclude_recursion": false,
      "position": "system_note",
      "insertion_order": 100,
      "priority": 50,
      "group": "",
      "group_weight": 100,
      "comment": ""
    }
  ]
}
```
