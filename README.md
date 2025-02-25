# AI狼人杀模拟器

一个基于大语言模型的多智能体狼人杀游戏模拟系统。通过配置不同的AI模型（如GPT-4、Claude、Gemini等）作为玩家，实现完整的狼人杀游戏流程。

## 项目状态

✅ 基础功能已完成，可以正常运行  

✅ 统计功能已完成，可以正常统计模型轮流扮演角色的时候，胜率等信息了

📝 目前正在让代码跑N轮并撰写相关论文  

🔨 论文挂arxiv后给这个项目加上GUI

🔨 持续优化中...

## 功能特点

- 支持多种角色：狼人、村民、预言家、女巫、猎人
- 支持多个AI模型：GPT-4、Claude、Gemini、DeepSeek等
- 完整的游戏流程：夜晚行动、白天讨论、投票处决
- 丰富的角色技能：预言家查验、女巫救人/毒人、猎人开枪
- 真实的对话系统：AI角色会进行符合身份的对话和行为
- 完整的游戏记录：保存所有对话和行动记录
- AI轮流扮演角色，可以统计每个AI扮演不同角色胜率

## 安装使用

1. 克隆项目：
```bash
git clone https://github.com/your-username/AIWolfGame.git
cd AIWolfGame
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置AI模型：
在 `config/ai_config.json` 中配置你的AI模型API密钥：
```json
{
  "ai_players": {
    "gpt-4": {
      "api_key": "your-openai-api-key",
      "model": "gpt-4",
      "baseurl": "https://api.openai.com/v1"
    },
    "claude35": {
      "api_key": "your-anthropic-api-key",
      "model": "claude-3-sonnet-20240229"
    }
    // ... 其他AI模型配置
  }
}
```

4. 配置游戏角色：
在 `config/role_config.json` 中配置游戏角色：
```json
{
  "game_settings": {
    "total_players": 8,
    "day_time_limit": 180,
    "night_time_limit": 60
  },
  "roles": {
    "werewolf": {
      "wolf1": {
        "ai_type": "gpt-4",
        "name": "张大胆",
        "personality": "狡猾"
      }
    },
    "seer": {
      "seer1": {
        "ai_type": "gpt-4",
        "name": "王智",
        "personality": "冷静"
      }
    }
    // ... 其他角色配置
  }
}
```

5. 运行游戏：
```bash
python main.py --rounds 1 --delay 0.5 --export-path ./test_analysis1
```

rounds: 游戏轮数
delay: 每轮之间的延迟时间
export-path: 导出分析结果的文件路径

## 运行效果展示

以下是一个游戏回合的示例：

```
=== 游戏开始 ===

=== 第 1 回合 ===

=== 夜晚降临 ===

狼人们正在商讨...

张大胆 的想法：
【张大胆靠在椅背上，双手交叉在胸前，眼神似乎漫不经心地扫过其他玩家】
"今天的局势真是有点意思啊。" 

"咱们先从场上的表现来看吧。王智这个人发言不多，但总给我一种很有观察力的感觉，
尤其是他看人的眼神，总觉得能把人看穿似的。这种人留着，可能会是个隐患啊。"

...（更多精彩对话）

=== 天亮了 ===

=== 开始轮流发言 ===

【第一轮发言】

王智 的发言：
【王智微微蹙眉，双手交叉在胸前，目光锐利地扫过桌上众人】
"大家好，既然是第一轮，我们得抓紧时间分析。我想先提个建议，
不妨每个人都简单说说自己的身份和观点。这样，我们也许能从细节里发现一些问题。"
```

## 项目结构

```
werewolf-ai/
│
├── config/
│   ├── ai_config.json       # AI模型配置
│   └── role_config.json     # 角色分配配置
│
├── game/
│   ├── __init__.py
│   ├── game_controller.py   # 游戏主逻辑
│   ├── ai_players.py        # AI玩家基类/实现
│   └── roles.py            # 角色定义
│
├── utils/
│   ├── logger.py           # 日志记录器
│   └── game_utils.py       # 通用工具函数
│
├── logs/                   # 自动生成的日志目录
│
└── main.py                 # 程序入口
```

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 论文引用

如果你在研究中使用了本项目，请引用我们的论文（即将发布）或Github.



