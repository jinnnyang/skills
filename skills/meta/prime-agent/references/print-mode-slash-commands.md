Print 模式可用的 slash commands — prime-agent CLI 参考

用法：
  prime-agent -p "/compact [instructions]"      # text 模式
  prime-agent -p --mode json "/goal xxx"        # json 模式可看完整事件流
  prime-agent -p --no-session "/goal xxx"       # 不落盘
  prime-agent -p --session-dir <dir> "/goal x"  # 指定会话保存目录
    ⚠ 0.10.0 实测：不带 --session-dir 时 print 模式会话不落盘（in-memory），
      /goal 的持久化必须配 --session-dir 或 PRIME_AGENT_SESSION_DIR。

════════════════════════════════════════════
一、print 模式真正执行的 session 命令（4 个）
════════════════════════════════════════════
来源：SESSION_SLASH_COMMAND_NAMES（crates/pa-types/src/slash_commands.rs）+
execute_session_command 的 match（crates/pa-core/src/session_engine/session_commands.rs）。

/compact [instructions]
    压缩会话上下文；可选 instructions 聚焦摘要重点。
    json 模式事件：compaction_start → compaction_end（manual）。
/refine [instructions]
    精炼 harness prompt notes、skills、subagents、memory。
/goal <objective> | /goal pause|resume|clear
    设置/查看持久目标（支持暂停、恢复、清除）。
    成功返回 goal_update 事件；配 --autonomous 连续推进。
/autonomous [budget]
    设置/查看自主模式与可选预算；由 flag（--autonomous-gate 等）细控。

其余全部 builtin 命令（/model、/tree、/settings…）在 print 模式下
parse 得到但 is_session_slash_command_name 为 false，不执行、原样当
prompt 处理（或报 unknown）。

════════════════════════════════════════════
二、CLI 等价的进程级功能（不是 slash，是子命令）
════════════════════════════════════════════
  prime-agent sessions        ← /agents（agent 状态/活动/用量；需 daemon）
  prime-agent agents          ← agents 搜索视图
  prime-agent model           ← /model（检查可用模型）
  prime-agent mcp             ← /mcp 服务端部分（用户 MCP 管理）
  prime-agent package         ← 包管理（skills/prompts/themes）
  prime-agent config          ← 包资源配置
  prime-agent telemetry       ← /telemetry
  prime-agent factory         ← /factory 机器库
  prime-agent prompt          ← /system-prompt（打印组装后的系统提示词+分层）
  prime-agent schedule        ← /heartbeat 相关定时
  prime-agent stop/rename/send/attach ← daemon agent 操作
  prime-agent session export  ← 会话导出 HTML
  prime-agent doctor / incident / shutdown / status
  prime-agent update          ← /update

════════════════════════════════════════════
三、全部 builtin 命令表（TUI 用；print 模式不可用，仅备查）
════════════════════════════════════════════
Client 端（TUI-only）命令，含别名与参数提示：
  /settings                         打开设置菜单
  /model                            模型选择器
  /effort (/thinking) [level]       思考等级选择器
  /fast                             OpenAI Fast 模式开关
  /tier [default|flex|priority|auto] 服务档位
  /name (/rename) [name]            会话显示名
  /session                          会话信息
  /system-prompt                    显示发给模型的完整系统提示词
  /logs                             日志位置
  /traces [status|on|off|preview|upload|upload-current|upload-all|login]
  /telemetry                        遥测开关
  /context (/usage)                 token/成本/上下文用量
  /changelog                        更新日志
  /update                           更新到最新 Rust 构建
  /nightly [on|off|status]          nightly 通道
  /hotkeys                          快捷键表
  /fork                             从历史用户消息分叉
  /clone                            在当前位置复制会话
  /tree                             会话树导航（切分支）
  /login /logout                    provider 认证
  /mcp                              MCP 连接菜单
  /plugins [search]                 外部服务
  /new (/clear) [--name "n" --] [prompt]  新会话
  /rlm-max-depth                    每会话 RLM 最大深度
  /heartbeat                        持久心跳
  /heartbeats                       心跳管理
  /factory                          工厂开关
  /resume [path|id]                 恢复会话
  /reload                           重载 keybindings/skills/prompts/themes
  /speed [on|off]                   tok/sec 页脚
  /export [path]                    导出（.html/.jsonl）
  /import <path.jsonl>              导入并恢复
  /share                            分享为 secret gist
  /copy                             复制最后回复
  /btw (/side) <question>           旁路提问（不入会话）
  /quit                             退出

来源：CANONICAL_BUILTIN_SLASH_COMMANDS（crates/pa-types/src/slash_commands.rs:40）。
