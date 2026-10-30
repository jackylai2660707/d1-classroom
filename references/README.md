# 原廠資料與歷史歸檔

原廠 SDK 的正式部署副本已直接納入 Git：`d1-classroom/bridge/sdk/`。正常部署不需另下載 SDK。

完整參考資料保存在私人 Release 的 `D1-References-2026-10-30.zip`。在倉庫根目錄執行：

```powershell
powershell -NoProfile -File scripts/fetch-release.ps1 -IncludeReferences
```

腳本先核對 SHA-256，再解壓到本目錄，包含：

- 原廠產品手冊與 SDK 開發指南。
- SDK 原包副本、URDF 與 STEP 外觀模型。
- 原有研究摘錄與參考圖片。
- 歷史教材/1.0-20261020：舊版 Word / PPT / PDF、舊交付與原始碼。
- 歷史建置/1.0-20261021：舊教材生成腳本與定稿 PDF，保留供回溯，不是目前建置入口。

大型模型與歷史二進位檔不放入 Git 歷史；Release 保留其完整內容與檔案清單。原廠資料的權利和授權維持原狀。需要修改現有程式，先看根目錄 README、docs/索引.md 與 d1-classroom/README.md。
