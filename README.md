# DeskpetRant — Rant机 吐槽桌宠

<p align="center">
  <img src="pictures/rantRobert_normal.png" alt="Rant机（常规表情）" width="96" height="96">
</p>

一个住在桌面上的像素小方块「Rant机」。它会定时看一眼你的屏幕，冒出一句吐槽或闲聊；
点它一下可以打开对话框陪聊，还能把聊过的事记在本地。不想被看时，让它「闭眼」即可，
它会彻底停止截屏。

## 功能

- **像素形象**：像素画小方块 + 表情切换（常规 / 开心·害羞 / 无语 / 疑惑·好奇 / 闭眼 / 兴奋·烦躁；清醒时偶尔眨眨眼）
- **表情联动**：吐槽和聊天回复都会按内容自动切换表情（模型附带情绪标签 + 本地关键词兜底）
- **屏幕吐槽**：按设定间隔截屏，交给视觉模型解读，偶尔弹一句吐槽；闭眼后完全停止
- **吐槽续聊**：点屏幕上的吐槽气泡（或聊天记录里点宠物消息）即可引用它接着聊；吐槽会自动收进聊天记录，气泡没来得及点也不会错过
- **聊天**：点击宠物弹出对话框，聊过的事会记住
- **互动反馈**：快速晃它 / 反复睁闭眼会露出烦躁表情吐槽「到底要怎样啦！」（闭眼中被吵也会短暂睁眼后睡回）；长按=戳它，清醒会撒娇、睡觉只说梦话
- **再说一句**：右键宠物或托盘菜单可让它立刻再截屏吐槽一句（没接网络时用本地短句兜底）
- **本地记忆**：对话历史存在本机 SQLite；每攒够 20 条对话自动压缩成记忆要点，退出时补一次
- **程序合成提示音**：吐槽/回复时播放复古哔声（开心上扬、无语低平、烦躁低音下行），可关闭
- **闭眼模式**：停止一切截屏识别，宠物进入睡觉表情
- **设置**：对话框左侧齿轮进入（服务商 / API key / 识别间隔 / 吐槽概率 / 提示音 / 开机自启 / 闭眼 / 查看记忆 / 清空记忆）
- **托盘**：右键菜单可快速 对话 / 再说一句 / 设置 / 闭眼 / 退出

## 给使用者的快速开始

成品 exe 不放进 Git 仓库（dist/ 被 .gitignore 忽略），请到 Releases 页面下载：

1. 打开 [Releases](https://github.com/fu0an/Deskpet_Rant/releases)，下载最新版压缩包（内含 `Rant机.exe`）
2. 解压后双击 `Rant机.exe`，无需安装 Python
3. 点桌面上的小方块 → 左侧齿轮 → 设置
4. 选服务商（默认智谱 GLM），粘贴 API key
5. 保存，开始吐槽

### 获取 API key

| 服务商 | 哪里申请 |
|---|---|
| 智谱 GLM（推荐） | https://open.bigmodel.cn/ ，控制台创建 API key，视觉与聊天通用，有免费档 |
| 阿里云百炼 | https://dashscope.console.aliyun.com/ |
| OpenAI | https://platform.openai.com/ |
| Moonshot | https://platform.moonshot.cn/ |

> 隐私：屏幕识别会把**截图发送给你选择的 API 服务商**。「闭眼」后彻底停止截屏。
> 聊天记录和记忆都只保存在本机。

## 开发（从源码运行）

环境：Windows + Python 3.10+，无需显卡（识别都在云端）。

仓库只上传源码，`.venv/` 不会一起提交，需要自己创建。**不要直接用系统 `python` 跑源码**，否则会报 `No module named 'PySide6'`；必须用下面建好的 venv 里的 python：

```powershell
# 1. 创建虚拟环境（只要建过一次即可）
python -m venv .venv

# 2. 安装运行依赖
.\.venv\Scripts\python -m pip install -r requirements.txt

# 3. 启动
.\.venv\Scripts\python src\main.py
```

### 打包 exe

先完成上面第 1、2 步（建好 `.venv` 并装好运行依赖），再执行：

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\pyinstaller deskpet.spec
```

产物在 `dist\Rant机\`。发布时把整个 `Rant机` 文件夹压缩成 zip，作为附件上传到 GitHub Releases——README「快速开始」里的下载链接就指向它。

> 提示：若上两条命令报「系统找不到指定的路径」，是因为还没执行 `python -m venv .venv`（或 venv 不在当前目录）。

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
`rantRobert_eyesClosed.png`、`rantRobert_excitedORrestless.png`），运行时会按表情加载并最近邻放大到窗口尺寸。
眨眼复用 `rantRobert_eyesClosed.png` 短暂闪眨，不需要额外动画素材。
替换图片：保持同名、同尺寸覆盖即可；打包 exe 时 `deskpet.spec` 会自动带上该目录。


