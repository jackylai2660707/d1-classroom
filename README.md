# D1 機器狗實驗室 2.0

**公司電腦繼續開發：先看 [跨電腦持續開發](docs/跨電腦持續開發.md)。實機部署按 [公司電腦實機測試](docs/公司電腦實機測試.md)。**

新狗開發版初始化：雙擊根目錄「初始化新機器狗.cmd」，輸入當前 IP。先讓狗趴穩並斷開控制端；支援範圍、備份與失敗還原見 [一鍵初始化說明](docs/一鍵初始化機器狗.md)。不同韌體不會自動猜測修改，初始化不測動作。

本機最新版成品為 2.1.0，根目錄「啟動學生工坊.cmd」可直接開啟，已包含擴充動作、感測資料及持續辨識。繼續改程式時用「啟動學生工坊開發版.cmd」，啟動時重新 bundle；不要同時開兩版連同一隻狗。2.1.0 的本機交付與驗證範圍見 [打包紀錄](docs/2.1.0打包紀錄.md)，舊 v2.0.0 下載清單保持原樣。

私人倉庫：[jackylai2660707/d1-classroom](https://github.com/jackylai2660707/d1-classroom)。Git 保存可維護原始碼、完整原廠 SDK 與文檔；Windows 成品及大型參考資料放同一私人倉庫的 Release。

開發版：clone 後在倉庫根目錄執行 `powershell -NoProfile -File scripts/setup-dev.ps1`，再進 `d1-classroom` 執行 `pnpm run dev`。可修改 UI、功能與橋接、連真機 debug，再以正常 Git 分支 commit / push；不需要使用預先打包的 EXE。

以下是取得固定 Release 成品的流程，供比對與現場驗收基準使用：

```powershell
gh auth login
gh repo clone jackylai2660707/d1-classroom
cd d1-classroom
powershell -NoProfile -File scripts/fetch-release.ps1
powershell -NoProfile -File scripts/preflight.ps1
```

取得成品後，雙擊 output/D1彩色課程套件/使用說明.html。已有本地成品可直接開啟；下載腳本保留既有資料，更新時加 -Replace。完整原廠與歷史資料可加 -IncludeReferences 取得。

16 課離線網頁教程、Windows 學生工坊、工作紙、教師手冊、同一份機器狗初始化包與完整原廠 SDK 已整合成一套。學生工具可在根目錄雙擊「啟動學生工坊.cmd」。

- 學生：首頁 → 學生開始 → 本課教程；工具內也有「本課教程」按鈕。
- 教師：首頁 → 教師帶課；列印資料/ 包含三份 PDF。
- 技術人員：首頁 → 設備部署；原廠 SDK 已包含在初始化包中。
- 整套交付：output/D1彩色課程完整套件.zip。

第 12 課自主訓練需要外部網站及網路；教程、學生工具、備用模型分類測試可離線使用。真機初始化、動作與停止仍須完成現場驗收，未驗收前保持練習模式。

## 工作區目錄

```text
output/                       當前正式交付與完整 ZIP
  D1彩色課程套件/
    使用說明.html             唯一課程入口
    啟動學生工坊.cmd
    教程/                     16 課、學生、教師、部署指南
    列印資料/                 16 頁工作紙、18 頁教師手冊、5 頁操作、試教與色卡
    學生工具/                 Windows x64 成品
    配套檔案/                 JSON / Python、圖片、模型
    技術人員部署/             自帶 SDK 初始化 ZIP、技術文件
    D1學生工坊與教材原始碼.zip
  D1彩色課程完整套件.zip
  D1機器狗初始化包.zip

d1-classroom/                 可維護的原始碼
  curriculum/lessons.json      課程唯一內容來源
  curriculum/projects/        自課程資料匯出的 32 份起步檔
  courseware/                 網頁版式、互動與維護說明
  app/                       Windows 工具、積木、相機與模型
  bridge/                    初始化、systemd 與原廠 SDK
  assets/                    原廠圖與實際工具截圖
  build/                     生成、打包及驗證證據
  tests/                     核心、假 SDK 與離線教程驗證

docs/                        工作索引、測試與變更紀錄
scripts/                     工作區測試及索引工具
references/                  完整原廠與歷史資料，按需從私人 Release 下載
  歷史教材/1.0-20261020/       已歸檔的舊 Word / PPT / PDF 與舊入口
  歷史建置/1.0-20261021/       舊生成腳本與定稿 PDF
releases/                    固定版本下載清單、大小與 SHA-256
field-results/               公司現場記錄（Git 忽略）
```

後續工作先看 [工作索引](docs/索引.md)，重建步驟看 [原始碼說明](d1-classroom/README.md)。根目錄執行 powershell -NoProfile -File scripts/test.ps1 跑核心測試；修改檔案後用 python scripts/update_index.py 更新索引。

Git 不追蹤 node_modules、output 成品、歷史二進位檔、真機設定、公司日誌與學生作品。拉取後修改程式見 [開發重建](d1-classroom/README.md)；需要來源清單可執行 python scripts/update_index.py 產生本地索引。
