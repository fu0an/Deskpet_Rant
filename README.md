# DeskpetRant — Rant机 吐槽桌宠

一个住在桌面上的像素小方块「Rant机」。它会定时看一眼你的屏幕，冒出一句吐槽或闲聊；
点它一下可以打开对话框陪聊，还能把聊过的事记在本地。不想被看时，让它「闭眼」即可，
它会彻底停止截屏。

## 功能

- **像素形象**：像素画小方块 + 表情切换（常规 / 开心·害羞 / 无语 / 疑惑·好奇 / 闭眼）
- **表情联动**：吐槽和聊天回复都会按内容自动切换表情（模型附带情绪标签 + 本地关键词兜底）
- **屏幕吐槽**：按设定间隔截屏，交给视觉模型解读，偶尔弹一句吐槽；闭眼后完全停止
- **聊天**：点击宠物弹出对话框，聊过的事会记住
- **本地记忆**：对话历史存在本机 SQLite；每攒够 20 条对话自动压缩成记忆要点，退出时补一次
- **程序合成提示音**：吐槽/回复时播放复古哔声（开心上扬、无语低平），可关闭
- **闭眼模式**：停止一切截屏识别，宠物进入睡觉表情
- **设置**：对话框左侧齿轮进入（服务商 / API key / 识别间隔 / 吐槽概率 / 提示音 / 开机自启 / 闭眼 / 查看记忆 / 清空记忆）
- **托盘**：右键菜单可快速 对话 / 设置 / 闭眼 / 退出

## 给使用者的快速开始

1. 双击 `Rant机.exe`（或运行 `python src/main.py`）
2. 点桌面上的小方块 → 左侧齿轮 → 设置
3. 选服务商（默认智谱 GLM），粘贴 API key
4. 保存，开始吐槽

### 获取 API key

| 服务商 | 哪里申请 |
|---|---|
| 智谱 GLM（推荐） | https://open.bigmodel.cn/ ，控制台创建 API key，视觉与聊天通用，有免费档 |
| 阿里云百炼 | https://dashscope.console.aliyun.com/ |
| OpenAI | https://platform.openai.com/ |
| Moonshot | https://platform.moonshot.cn/ |

> 隐私：屏幕识别会把**截图发送给你选择的 API 服务商**。「闭眼」后彻底停止截屏。
> 聊天记录和记忆都只保存在本机。

## 开发

环境：Windows + Python 3.10+，无需显卡（识别都在云端）。

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python src\main.py
```

### 打包 exe

```powershell
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\pyinstaller deskpet.spec
```

产物在 `dist\Rant机\`。

## 目录结构

```
src/
├── main.py                 # 入口，组装所有模块 + 托盘
├── config.py               # 设置读写 + 服务商预设
├── autostart.py            # 开机自启（HKCU Run）
├── settings_view.py        # 设置面板（含查看记忆）
├── sound.py                # 程序合成提示音
├── llm/                    # client.py 统一 OpenAI 兼容调用；prompts.py 人设/吐槽/记忆提示词
├── chat/                   # main_dialog.py 贴宠对话框（聊天/设置双视图）；chat_engine.py 对话逻辑
├── vision/                 # capture.py 截屏降采样；screen_observer.py 定时观察
├── memory/                 # store.py SQLite 本地记忆；summarizer.py 对话压缩成记忆要点
└── pet/                    # pet_window.py 透明置顶窗口；sprite.py 像素形象；expressions.py 表情判定/控制；bubble.py 吐槽气泡
```

## 素材

形象为 24x24 的像素画，放在根目录 `pictures/`，每个表情一张 PNG（`rantRobert_normal.png`、
`rantRobert_happyORshy.png`、`rantRobert_haveNOwords.png`、`rantRobert_puzzledORcurious.png`、
`rantRobert_eyesClosed.png`），运行时会按表情加载并最近邻放大到窗口尺寸。
替换图片：保持同名、同尺寸覆盖即可；打包 exe 时 `deskpet.spec` 会自动带上该目录。

## 人设调整

性格要求、吐槽/聊天提示词都集中在 `src/llm/prompts.py`，一处修改即可生效。
