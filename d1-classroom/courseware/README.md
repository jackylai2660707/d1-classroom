# D1 課程套件 2.0 原始碼

正式入口是 output/D1彩色課程套件/使用說明.html。教程是普通離線網頁，不需要伺服器或安裝套件；第 12 課使用的外部訓練網站仍需網路。

- 內容唯一來源：curriculum/lessons.json，含教學內容、積木、Python 及 tutorial 版面資料。
- 本目錄：style.css、course.js，控制離線課件的排版與互動。
- 生成網頁：在 d1-classroom 執行 python build/courseware.py。
- 生成三份列印文件：使用安裝了 reportlab 的 Python 執行 python build/printables.py。
- 完整發佈：先 bundle、package，再執行 python build/deliver.py。
- 網頁與成品驗證：執行 node tests/courseware-smoke.cjs；Playwright 可用 D1_PLAYWRIGHT 指定。

課件不會直接控制機器狗。所有動作只透過學生工坊；程式與機器狗之間維持已驗證的控制流程。

網頁記錄支援匯出和匯入 JSON。不要依賴學校電腦的本機儲存，重啟還原前須將作品和記錄存到老師指定的持久位置。

產品照片和原廠 SDK 保留各自原有來源與授權。教程中的軟體畫面由實際學生工坊截取；掃描示例使用假 SDK 和測試 MAC，不代表真機驗收。
