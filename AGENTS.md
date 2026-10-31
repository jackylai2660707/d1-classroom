# 工作區維護指引

- 先讀 README.md、docs/索引.md 和 d1-classroom/README.md。
- 正式入口：output/D1彩色課程套件/使用說明.html。正式版本 2.0.0，以離線 HTML 教程與三份 PDF 交付，不重新加入 Word / PPT。
- 課程唯一來源是 d1-classroom/curriculum/lessons.json，包含教學內容、blocks、code 及 tutorial metadata。curriculum/build-content.cjs 只匯出起步檔，不重建或覆蓋課程文字。
- 網頁樣式與互動在 courseware/；生成入口 build/courseware.py、build/printables.py。生成 PDF 需遵守 PDF 技能的標記與渲染檢查。
- 修改 renderer.js 或課程資料後執行 pnpm run bundle；不要只改 renderer.bundle.js。package 只更新 EXE / ASAR；deliver.py 才重建 ZIP 與 SHA-256。
- 根目錄執行 powershell -NoProfile -File scripts/test.ps1。教程驗證用 tests/courseware-smoke.cjs --packaged；Playwright 可由 D1_PLAYWRIGHT 指定。
- 教程不會直接控制狗。工具的 tutorial IPC 只接受 1–16 課，固定開啟完整套件內的本地課件，不接受任意路徑。
- 學習記錄以 JSON 匯入 / 匯出，勿依賴學校電腦本地持久化。HTML 字段導入不可使用 innerHTML。
- 連線只有 Wi-Fi MAC、DHCP、UDP 廣播發現與單一控制憑證；不新增 UID、首次配對或多種連線模式。
- 每隻狗執行同一份含原廠 SDK 的 install.sh。bridge/sdk 保留原包、BSD 授權與 manifest；正常部署不要求另備 SDK。
- 假 SDK、軟體測試及練習模式不代表實機驗收。未現場確認動作 / 停止 / 相機與整班負載前，不宣稱可直接實機授課。
- robot.json、.previous、學生作品、實際控制憑證與執行日誌不能加入交付。
- 1.0 Word / PPT / PDF 與舊入口已歸檔到 references/歷史教材/1.0-20261020。舊建置腳本與定稿 PDF 已移到 references/歷史建置/1.0-20261021，完整參考資料隨私人 Release 歸檔；不把歷史內容混入 2.0。
- 增刪移動後更新 docs 紀錄，執行 python scripts/update_index.py；工作區索引不同於正式交付檔案清單。

- 私人 GitHub 倉庫為 jackylai2660707/d1-classroom。Git 追蹤原始碼、bridge/sdk 與文檔；成品 / 大型歷史資料透過同倉庫私人 Release 交付，不用 Git LFS。
- 公司接手先讀 docs/公司電腦實機測試.md。下載腳本 scripts/fetch-release.ps1 按 releases/v2.0.0.json 核對 SHA-256；現場記錄保存在忽略的 field-results/。
- 跨電腦繼續開發先讀 docs/跨電腦持續開發.md。scripts/setup-dev.ps1 安裝鎖定的開發依賴；pnpm run dev / dev:debug 以目前原始碼啟動，不使用舊 Release EXE。
- 開發電腦可使用 Windows 11 ARM64；正式 Windows 成品統一以 Intel / AMD x64 為目標，不支援 32 位元 x86 Windows。安裝及打包時必須使用 Windows x64 Electron 與 FFmpeg，不得因本機 Node.js 是 ARM64 就改成交付 ARM64。現有 setup-dev.ps1 / package.cjs 尚未自動固定目標架構；具體要求見 docs/跨電腦持續開發.md「Windows ARM 開發與 x64 交付」。
- 不因開發電腦是 ARM64 就新增例行多架構驗證或要求使用者反覆換機測試；按修改範圍執行既有必要檢查。文檔中的 x64 交付要求不代表已完成 ARM 相容性或 x64 成品驗收，實機動作 / 停止 / 相機驗收仍按原有規範。
- 不覆寫已發佈的 Release 標籤或 manifest；新成品需新版本與新清單。推送前執行 scripts/check_repository.py 及核心測試。
