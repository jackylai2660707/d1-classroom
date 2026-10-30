# 成品下載與重建

Git 只追蹤這份說明。Windows 成品、PDF、完整 ZIP 與初始化包保存在同一個私人 GitHub 倉庫的 Release。

從倉庫根目錄執行：

```powershell
gh auth login
powershell -NoProfile -File scripts/fetch-release.ps1
```

腳本以倉庫內的 releases/v2.0.0.json 核對每個下載的 SHA-256，再將完整套件解壓到本目錄；既有成品不會被直接覆蓋，更新時加 `-Replace`，舊成品移到 output/.previous-releases/。

完成後雙擊 D1彩色課程套件/使用說明.html，或從倉庫根目錄雙擊啟動學生工坊.cmd。

也可按 d1-classroom/README.md 從原始碼重建，無須下載成品。請勿將公司實測資料放進交付成品；結果另存 field-results/。
