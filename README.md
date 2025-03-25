# AI狼人杀游戏与信任网络分析

## 项目介绍

这是一个基于AI大模型的狼人杀游戏系统，集成了信任评分系统，用于研究AI模型在社交游戏中的信任关系与决策行为。

## 主要功能

- AI驱动的狼人杀游戏引擎
- 完整的游戏流程：夜晚杀人、白天讨论、投票处决
- 多种角色支持：狼人、村民、预言家、女巫、猎人
- 信任评分系统：AI玩家对其他玩家的信任度评估
- 数据收集与分析：收集信任评分、投票行为与角色信息
- 信任网络可视化：基于信任评分构建动态信任网络

## 信任评分系统

系统中每个AI玩家在游戏过程中会对其他玩家进行信任度评分（0-10分），评分基于：

1. 其他玩家的发言一致性与逻辑性
2. 投票行为的合理性
3. 与自身判断的一致程度
4. 是否有欺骗或隐瞒的迹象

这些评分会随游戏进程动态变化，并与投票行为相关联，形成动态的信任网络。

## 数据分析功能

项目提供了专用的数据分析工具，支持：

1. 读取游戏数据并解析成结构化形式
2. 生成信任网络图（基于NetworkX）
3. 分析信任关系与投票行为的相关性
4. 比较同阵营和跨阵营的信任评分差异
5. 导出处理后的数据以供进一步分析

## 安装与使用

安装依赖：

```bash
pip install -r requirements.txt
```

运行游戏：

```bash
python main.py --config config.json
```

分析游戏数据：

```bash
python utils/trust_network_analysis.py game_data/ --analyze-votes --export --output analysis_results/
```

## 数据收集

每场游戏会收集以下数据：

1. 信任评分：每轮每个模型对其他模型的信任度（0-10分）
2. 投票行为：每轮每个模型的投票选择和理由
3. 角色信息：每个模型的实际角色（狼人、村民等）
4. 游戏元数据：轮次、最终结果等
5. 发言内容：每轮中每个模型的文本内容

所有数据以JSON格式保存，可用于后续研究分析。

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



