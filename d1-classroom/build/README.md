# 建置入口與歷史腳本

2.0 的正式教程使用 HTML / CSS，列印資料使用 ReportLab，不再以 Word 或 PPT 為主稿。

| 目前入口 | 用途 |
|---|---|
| curriculum/build-content.cjs | 由唯一來源 lessons.json 匯出 16 份 JSON 與 16 份 Python |
| bundle.cjs | 打包學生工坊 renderer、Skulpt 與 Blockly media |
| package.cjs | 使用暫存目錄建置 Windows 成品與第三方授權 |
| capture-courseware.cjs | 截取目前實際工具畫面；MAC 掃描使用假 SDK |
| courseware.py | 生成首頁、16 課教程、4 份指南，無外部執行依賴 |
| printables.py | 生成 16 頁工作紙、18 頁教師手冊、5 頁操作 / 試教 / 色卡 |
| deliver.py | 檢查 SDK 與新版內容，生成初始化、原始碼、完整套件 ZIP 及 SHA-256 |
| qa/courseware/ | 目前網頁、PDF 與交付驗證證據 |

完整命令見上一層 README。網頁主題與互動在 courseware/，課程內容在 curriculum/lessons.json。更新內容後必須同時重建起步檔、bundle、教程、PDF、package 與完整交付。

舊版 books.py、slides.mjs、舊截圖工具與定稿 PDF 已移至 references/歷史建置/1.0-20261021，隨私人 Release 的參考資料 ZIP 保留，不在目前 Git 原始碼中。舊 artifact-tool 依賴不需要還原；現有本機 node_modules 由 Git 忽略。

新版不依賴 @oai/artifact-tool、LibreOffice 或 PowerPoint。請從本文列出的入口工作。
