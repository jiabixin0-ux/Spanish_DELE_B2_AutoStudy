# DELE B2 西语每日自动学习系统

这个项目会把 `materials/dele_material.pdf` 提取成文本，再按照 DELE B2 备考目标重新组织成每日学习邮件。它不会简单按页码切分 PDF，而是按主题、语法、交际功能和精读材料来生成课程。

## 项目结构

```text
materials/dele_material.pdf          原始学习资料
src/dele_b2_auto_study/pdf_extract.py        PDF 文本提取
src/dele_b2_auto_study/split_knowledge.py    知识点拆分与 B2 重组
src/dele_b2_auto_study/generate_daily.py     每日学习内容生成
src/dele_b2_auto_study/send_email.py         Gmail 邮件发送
data/raw/                              PDF 提取结果
data/processed/                        知识库
output/daily/                          每日课程 markdown/html
logs/                                  日志目录
run_daily.sh                           每日自动运行入口
```

## 安装

```bash
python3 -m pip install -r requirements.txt
```

## 配置 Gmail

不要把邮箱密码或授权码写进代码。发件人和收件人邮箱在 `config.yaml` 里配置，Gmail 应用专用密码只从环境变量 `GMAIL_APP_PASSWORD` 读取。

```bash
export GMAIL_APP_PASSWORD="your_16_character_gmail_app_password"
```

在 GitHub Actions 中，请把这个值保存为仓库 Secret：`GMAIL_APP_PASSWORD`。

## 手动运行一次

```bash
./run_daily.sh
```

首次运行会做四件事：

1. 提取 PDF 文本到 `data/raw/`
2. 生成 B2 目标知识库到 `data/processed/knowledge_base.json`
3. 生成当天课程到 `output/daily/latest_lesson.md` 和 `output/daily/latest_lesson.html`
4. 通过 Gmail 发送邮件

如果只想测试邮件配置但不发送：

```bash
PYTHONPATH=src python3 -m dele_b2_auto_study.send_email --dry-run
```

## 每天早上 8 点自动发送

GitHub Actions 会在每天北京时间早上 8:17 自动运行，也可以在 GitHub 页面手动触发。选择 8:17 是为了避开 GitHub Actions 每小时整点的高负载窗口，降低定时任务被延迟或丢弃的概率：

```text
Actions -> Daily DELE B2 Study Email -> Run workflow
```

如果在本机使用 cron，运行：

```bash
crontab -e
```

加入这一行，把 `/path/to/Spanish_DELE_B2_AutoStudy` 换成当前项目路径：

```cron
0 8 * * * cd /path/to/Spanish_DELE_B2_AutoStudy && /bin/zsh run_daily.sh >> logs/daily.log 2>&1
```

注意：cron 可能读不到你终端里的环境变量，需要确保 `GMAIL_APP_PASSWORD` 在运行环境中可用。

## 单独运行各步骤

```bash
PYTHONPATH=src python3 -m dele_b2_auto_study.pdf_extract --force
PYTHONPATH=src python3 -m dele_b2_auto_study.split_knowledge --force
PYTHONPATH=src python3 -m dele_b2_auto_study.generate_daily
PYTHONPATH=src python3 -m dele_b2_auto_study.send_email
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 说明

- 每日内容是一份 20-30 分钟可完成的学习讲义：先学 6-8 个核心表达、2-3 个句型、1 个语法点和 1 段精读，再完成少量分级输出练习、小测试、答案解析和间隔复习。
- `data/progress.json` 会记录学习起始日期和当天循环进度。
- `data/review_cards.json` 会记录间隔复习卡片。
- 原材料约 B1，脚本会围绕 DELE B2 的表达、连接、语法和任务要求做升级组织。
