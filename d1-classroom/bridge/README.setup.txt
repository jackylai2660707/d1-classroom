D1 新機器狗初始化：先分清楚你下載的是哪個包
================================================

如果你的電腦是 Windows，而且希望「只輸入 IP」：

1. 到私人 GitHub Release 下載 D1-Classroom-2.1.0-Windows-x64.zip（完整套件）。
2. 在檔案總管右鍵 ZIP → 全部解壓縮。不要在 ZIP 預覽視窗內雙擊程式。
3. 開啟解壓後的：
   D1彩色課程套件 → 技術人員部署 → 一鍵初始化
4. 雙擊「初始化新機器狗.cmd」。
5. 輸入新狗當前 IP，按 Enter。預設帳號／密碼由工具處理，不需另行輸入。
6. 等待「初始化成功」和完整 Wi-Fi MAC；沒有成功訊息就不要當作完成。
7. 開啟套件根目錄的「啟動學生工坊.cmd」→ 掃描 → 核對同一 MAC → 連線。

Windows 初始化電腦需要 Python 3、內建 OpenSSH，以及 PuTTY Plink。
如果顯示缺少工具，先安裝所缺工具，再重開 CMD；不要把 Linux 的 install.sh
當成 Windows 安裝程式。學生平常使用學生工坊 EXE 不需要這些開發工具。

你目前這個 d1-setup 資料夾，是「在狗的 Linux 系統上執行」的部分。
它沒有 Windows 的輸入 IP 視窗。只下載這個包時，也可以按下面手動流程操作。

手動流程：只使用你已下載的狗端 ZIP
================================

準備：讓狗趴穩、保持靜止，停止學生程式並斷開所有控制端。
現場人員先確認原廠硬體停止方式。PC 與狗連同一個 Wi-Fi；不需網際網路。
狗開 AP 時 PC 可連狗的 AP，再使用其實際 IP。

步驟一【在 Windows 做】

把下載的 D1-Robot-Setup-2.1.0.zip 複製到「下載」資料夾，改名 d1-setup.zip。
保留 ZIP，不要只上傳 install.sh。注意不要改成 d1-setup.zip.zip。

開啟 PowerShell，逐行貼上：

  cd "$HOME\Downloads"
  $RobotAddress = Read-Host '輸入新機器狗的 IP'
  scp .\d1-setup.zip "firefly@${RobotAddress}:~/d1-setup.zip"
  ssh "firefly@$RobotAddress"

第一次 SSH 主機指紋確認，請核對 IP 與現場設備後接受。
要求密碼時輸入 firefly，再按 Enter；畫面不顯示字元是正常的。
上傳／登入出錯就先停下，不要繼續後面的狗端命令。

步驟二【SSH 成功後，在機器狗的終端做】

  python3.10 -m zipfile -e ~/d1-setup.zip ~/d1-new-setup
  cd ~/d1-new-setup/d1-setup
  python3.10 provision.py --probe
  sudo python3.10 provision.py --apply

若解壓目錄已存在，先換一個新的目錄名稱，避免混入舊版檔案。
sudo 要求密碼時仍輸入 firefly。

--probe 只讀檢查，輸出 problems 應為 []；有項目代表需要核對，不要猜測修改。
--apply 會再次檢查，對未知機型／韌體拒絕安裝；符合版本才備份、安裝橋接、
設定機內回環通訊，必要時單獨重啟原廠運控，最後檢查 SDK 就緒。
不會執行站立、趴下、握手、跳躍或其他動作測試。

步驟三【還是在狗端終端做】

  systemctl is-active d1-classroom
  cat /opt/d1-classroom/機身標籤.txt

必須看到 --apply 結果包含 initialized: true、sdk_ready: true，以及服務 active。
記下完整 Wi-Fi MAC 和輸出的 backup 路徑。然後輸入 exit 離開 SSH。

步驟四【回到 Windows 做】

開啟學生工坊 → 掃描機器狗 → 核對完整 MAC → 連線，先保持練習模式。
狗端 ZIP 不包含學生工坊 EXE；若沒有工具，另下載完整課程套件。

重要限制與常見問題
==================

* 只自動支援已驗證的 XG、運控 0.5.1-xg、Ubuntu 22.04 ARM64／CPython 3.10，
  並核對原廠啟動腳本雜湊。外形相同不代表韌體相同；不符合時會停止。
* 不要直接跑舊說明的 sudo bash install.sh 作新狗的一鍵初始化。
  install.sh 是底層安裝入口，單獨使用不會自動處理原廠 SDK 回環通訊備份流程。
* 新狗預設不設開機自啟。如果重開狗，服務可能是 inactive；確認機身靜止後可 SSH
  執行 sudo systemctl start d1-classroom，再回學生工坊掃描。
* 初始化會啟動 SDK，可能接管原廠 App／手柄；運控重啟也會影響控制狀態。
  「不發動作指令」不等於完全不影響機身，仍需現場人員監看。
* 如顯示失敗／逾時，保持狗開機至少三分鐘，讓保護性還原有時間完成。
  不要盲目反覆安裝；保存錯誤文字，核對原廠版本和備份結果。
* 初始化成功不是動作／停止／相機／整班負載驗收。先逐項完成現場驗收。

以上命令適用包含 provision.py 的 2.1.0 狗端初始化包。
已發布的 2.1.0 ZIP 原附件不被這份新說明覆寫；這份清楚版指引會隨後續新包交付。
