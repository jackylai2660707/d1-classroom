# ARM 開發機現場準備

準備日期：2026-10-30。供 2026-10-31 首次初始化 D1、從目前原始碼連線與除錯使用。已知現場有原廠登入資料與路由器，狗尚未安裝本專案初始化包。

## 本機已備妥

- Windows 11 ARM64，Git、Python 3.13、OpenSSH 的 ssh / scp、Edge 已有。
- 專案 local/tools/ 保存校驗過官方 SHA-256 的 Node.js 24.18.0 x64、GitHub CLI 2.103.3 ARM64，以及 pnpm 11.0.9。保留系統原有 ARM Node.js。
- 應用依賴按 frozen lockfile 安裝，renderer bundle 與離線教程已生成；Electron 38.2.0 和 FFmpeg 執行檔已確認為 x64，FFmpeg 可啟動。
- local/test-tools/ 已安裝 Playwright 1.62.1，供既有除錯與 smoke 腳本使用；啟動開發版不需網路下載。
- v2.0.0 正式套件與初始化包已從私人 Release 下載，按 releases/v2.0.0.json 核對大小與 SHA-256。成品在 output/D1彩色課程套件/；狗端包在 output/D1機器狗初始化包.zip，已含原廠 SDK。
- GitHub CLI 下載時使用既有 Git credential manager 憑證取得私人 Release；未另寫入 token 或建立 gh 登入。明天開發與初始化不需要重新登入 GitHub。若日後直接使用 gh，先按正常流程登入。

local/、downloads/、field-results/ 與 output/ 成品皆為本機資料，不進 Git；搬動整份工作區時保留它們。本機工具沒有加入全域 PATH，使用下列入口即可。

## 從原始碼開發與除錯

在倉庫根目錄執行：

```bat
scripts\dev-local.cmd
```

每次啟動會重新 bundle，再打開目前原始碼的 x64 學生工坊。要主程序除錯：

```bat
scripts\dev-local.cmd --debug
```

主程序 inspector 僅綁 127.0.0.1:9229；renderer 用 Ctrl+Shift+I。不要在狗運動時暫停除錯斷點。

需要執行 pnpm、node 或現有測試時，用 `scripts\dev-local.cmd --shell` 打開已選 x64 Node.js 的終端；此終端已在應用 d1-classroom/ 目錄。`--check` 僅顯示 Node 架構與 pnpm 版本。本機入口固定使用 local/ 的上述版本；另一臺電腦仍按 setup-dev.ps1 正常安裝，不會自動下載這些本機工具。

不要用根目錄「啟動學生工坊.cmd」判斷剛改的原始碼是否生效，那個入口開的是固定 Release。不要同時用開發版和 Release 連同一隻狗。

## 明天首次連狗

1. 電腦與狗接到同一個允許互通及廣播的 IPv4 Wi-Fi 網段，路由器提供 DHCP，關閉 AP 用戶端隔離。從路由器查狗當下 IP；不需要固定 IP。VPN / 虛擬網卡若造成路由問題，再處理相應介面。
2. 核對機型與韌體支援 zsl-1 HighLevel，確認原廠硬體停止方法、機身保持靜止。狗端須有原廠相容 Linux / CPython 3.10；電腦端 Python 3.13 不影響這項要求。
3. 在倉庫根目錄 PowerShell 上傳包並登入。帳戶使用原廠提供的值，以下 firefly 僅為文件示例：

```powershell
$RobotAddress = '換成狗當下的IP'
$RobotUser = 'firefly'
scp ".\output\D1機器狗初始化包.zip" "${RobotUser}@${RobotAddress}:~/d1-setup.zip"
ssh "${RobotUser}@${RobotAddress}"
```

在狗端執行：

```sh
unzip -o ~/d1-setup.zip -d ~/
cd ~/d1-setup
sudo bash install.sh
systemctl is-enabled d1-classroom
systemctl is-active d1-classroom
cat /opt/d1-classroom/機身標籤.txt
```

4. 安裝須顯示初始化成功、SDK 就緒、服務 active；記下完整 Wi-Fi MAC，保持靜止重開狗，再確認服務自啟。若失敗，按既有部署指南排錯，不任意改原廠運動服務或 SDK 配置。
5. 執行 `scripts\dev-local.cmd --debug`，保持練習模式，掃描 → 核對完整 Wi-Fi MAC → 連線，先確認電量和斷開 / 重連。
6. 在練習模式先核對程式；再按現場停止方案，依既有指南逐項測站立、停止、趴下及 0.5 秒低速前進。相機使用 TCP 8554。詳細動作與停止判據見 [公司電腦實機測試](公司電腦實機測試.md)，本頁不代替實機驗收。

本機已預建 field-results/2026-10-31_首次實機測試.md，現場結果、MAC、IP 與日誌留在該忽略目錄。

## 網路與防火牆

所需通訊為 SSH TCP 22、掃描 UDP 8765、控制 TCP 8765、相機 TCP 8554。公司網路仍須允許電腦與狗互通。保持 Windows 防火牆啟用，不開對外轉發。

本次未變更網路設定或防火牆。若現場可信任的課室 LAN 上掃描被 Windows 防火牆攔截，可由管理員開 PowerShell，在倉庫根目錄執行：

```powershell
powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\allow-d1-network.ps1
```

此腳本只給目前路徑的開發版 Electron 和 Release 程式允許「私人網路、本地子網、來源 UDP 8765」的掃描回覆，不改網路類型或關閉防火牆。僅在確認是可信任路由器後，於 Windows 網路設定將該課室 Wi-Fi 設為私人網路；公司政策攔截時交由 IT 處理。本機目前沒有管理員權限，因此沒有預先套用此規則。

## 本次本機結果與界限

核心 JavaScript 7 項通過；Python 23 項中 22 項通過、1 項 Linux shell 在 Windows 跳過；Release 保護 2 項通過。開發版既有 app-smoke 通過練習、模型、回環 UDP / HTTP 掃描、MAC 連線、占用拒絕、假動作、斷線取消及重新連線。x64 開發視窗與 127.0.0.1:9229 主程序 inspector 已確認可啟動，啟動入口的 Node 架構及 pnpm 版本檢查通過。原有 preflight 的 Windows 主機條件已接受 ARM64，正式成品目標仍維持 x64；本機 preflight 全項通過。

這些是電腦端與假 SDK 結果，沒有連接實體 D1；狗端相容性、首次初始化、實體動作與停止、RTSP 和公司路由器互通，需到場才能確認。不額外加入例行多架構驗證流程，正式版本與 Release manifest 未變更。
