# D1 機器狗實驗室 2.0 原始碼

繼續開發先看 [跨電腦持續開發](../docs/跨電腦持續開發.md)。在倉庫根目錄跑 `scripts/setup-dev.ps1`，再於本目錄執行 `pnpm run dev`，即可用目前原始碼修改功能 / UI 並連真機。`pnpm run dev:debug` 加上僅限本機的主程序 inspector；renderer 用 Ctrl+Shift+I。

Git clone 後，從倉庫根目錄執行 scripts/fetch-release.ps1 取得私人 Release 成品；完整接手步驟見 ../docs/公司電腦實機測試.md。正式使用從完整套件的「使用說明.html」開始。學生不需要安裝 Node.js、Python 或 SDK。

## 修改與重建

Windows 作者環境使用 Node.js 22+、pnpm 11.0.9、Python 3，以及 requirements-author.txt 內的 PDF 套件。PDF 預設使用 Windows 的微軟正黑體；其他環境可透過 D1_FONT / D1_FONT_BOLD 指定相容的中文字型 TTF / TTC。Playwright 驗證需 Microsoft Edge，可用 D1_PLAYWRIGHT 指向已安裝的 playwright 模組。

在本目錄依序執行：

```powershell
pnpm install
python -m pip install -r requirements-author.txt
pnpm run curriculum
pnpm run bundle
python build/courseware.py
python build/printables.py
pnpm run package
python build/deliver.py
```

教程使用的 assets/ 操作圖已隨 Git 提交；只有工具介面改動時才需執行 node build/capture-courseware.cjs 重新截圖。生成教程不需要啟動伺服器或下載網站資源。修改課程後要同時生成網頁、PDF、bundle 和起步專案，避免不同步。

- 內容：curriculum/lessons.json；不再從硬編碼模板覆蓋課程文字。
- 網頁版式與互動：courseware/style.css、courseware/course.js。
- 生成入口：build/courseware.py、build/printables.py。
- 應用建置：pnpm run bundle、pnpm run package。
- 完整交付：build/deliver.py 生成自帶原廠 SDK 初始化 ZIP、原始碼 ZIP、SHA-256 及完整套件 ZIP。

原始碼 ZIP 已附驗收紀錄。沒有既有 output 時，依上述順序先生成教程、PDF 與 Windows 成品，再執行發佈。發佈腳本會檢查必要文件，不會把缺 SDK 或含舊版教材的目錄當成完整交付。

## 驗證

```powershell
pnpm test
python -m unittest discover -s tests -p '*_test.py'
node tests/courseware-smoke.cjs --packaged
node tests/packaged-smoke.cjs
node tests/app-smoke.cjs --packaged
```

後三項需要 playwright 與 Microsoft Edge。可使用獨立工具目錄安裝本次驗證的 Playwright 版本：

```powershell
# 在 Git 倉庫根目錄安裝測試工具，local/ 不進 Git
npm install --prefix local/test-tools --no-package-lock playwright@1.62.1
$env:D1_PLAYWRIGHT = (Resolve-Path local/test-tools/node_modules/playwright).Path
cd d1-classroom
node tests/courseware-smoke.cjs --packaged
```

這是可選的 UI 自動測試工具，成品使用與核心測試不需安裝。D1_PYTHON 可指定 Python。假 SDK、掃描與斷線測試不會操作真狗，也不能代替實機驗收。

教程記錄透過檔案匯出 / 匯入，不依賴學生電腦儲存狀態。課件只提供教學，所有機器狗控制仍由學生工坊執行。

## 機器狗部署

完整步驟見「技術部署與實機驗收.md」。每隻狗使用同一份含原廠 SDK 的 d1-setup.zip，登入後執行 sudo bash install.sh。路由器 DHCP 即可，學生掃描並核對完整 Wi-Fi MAC，無需 UID、配對、固定 IP 或設定檔。

SDK 原包、授權與雜湊位於 bridge/sdk。程式、模型與相機解碼在 Windows 執行，運行時須保持連線。Linux 機身需相容的原廠環境與 CPython 3.10。


## 完整 Git 倉庫的發佈與接手

- 根目錄 scripts/test.ps1 跑核心；scripts/check_repository.py 檢查 Git index 的必要文件、敏感檔名、憑證特徵、LF 與大型檔。
- scripts/prepare-release.py --version 新版本 在重建完整交付後準備新 Release ZIP 與新的版本清單；已存在的 manifest 拒絕覆寫。v2.0.0 保持原狀。
- build/qa/ 是本機驗證結果；正式歷史證據摘要在 docs/，現場公司資料另存 field-results/。
- 工作區以外的絕對作者路徑已從目前建置入口移除。Windows PDF 字型的預設路徑可用環境變數覆寫。
