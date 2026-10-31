"""Build the offline course website from curriculum/lessons.json; standard library only."""
from pathlib import Path
from html import escape as h
import json
import shutil

R = Path(__file__).resolve().parents[1]
OUT = R.parent / 'output' / 'D1彩色課程套件'
SITE = OUT / '教程'
LESSONS = json.loads((R / 'curriculum/lessons.json').read_text(encoding='utf-8'))
VERSION = json.loads((R/'package.json').read_text(encoding='utf-8'))['version']
GROUPS = [('01—05', '從認識到控制', '先學停止與連線，再研究順序、時間和方向。', range(1, 6)),
          ('06—10', '把想法寫成程式', '用重複、變數與條件，走向可閱讀的 Python。', range(6, 11)),
          ('11—15', '讓機器狗看見', '採集、訓練、測試，再讓可靠的條件觸發短動作。', range(11, 16)),
          ('16', '展示與解釋', '用作品、測試記錄和個人解釋，呈現學習成果。', range(16, 17))]


def lesson_name(i):
    return f'lesson-{i:02}.html'


def write(name, text):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def link(url, text, cls='', **attrs):
    extra = ''.join(f' {k}="{h(str(v), quote=True)}"' for k, v in attrs.items())
    return f'<a href="{h(url, quote=True)}" class="{cls}"{extra}>{h(text)}</a>'


def page(title, content, root=False, lesson=None):
    assets = '教程/static/' if root else 'static/'
    home = '使用說明.html' if root else '../使用說明.html'
    prefix = '教程/' if root else ''
    body = f'data-lesson="{lesson}"' if lesson else ''
    return f'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="D1 機器狗實驗室：16 課離線教程、學生工具與完整部署套件。">
<meta http-equiv="Content-Security-Policy" content="default-src 'self' data:; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'self'; form-action 'none'">
<title>{h(title)} · D1 機器狗實驗室</title><link rel="stylesheet" href="{assets}style.css"><script defer src="{assets}course.js"></script></head>
<body {body}><a class="skip" href="#main">跳到主要內容</a>
<header class="site-header"><div class="header-inner"><a class="brand" href="{home}"><span class="brand-mark">D1</span><span>機器狗實驗室<small>動手做，讓想法動起來。</small></span></a>
<nav aria-label="主導覽">{link(home+'#courses','課程地圖')}{link(prefix+'start.html','學生開始')}{link(prefix+'teacher.html','教師帶課')}{link(prefix+'deploy.html','設備部署')}</nav></div></header>
<main id="main" class="page">{content}</main>
<footer class="site-footer"><span>D1 課程套件 {VERSION} · 2026.10</span><span>16 課 × 45 分鐘 · 積木 / Python / 圖像分類</span>{link(prefix+'about.html','版本、來源與驗收範圍')}</footer>
<dialog id="image-dialog" aria-label="放大操作圖"><button type="button" class="dialog-close">關閉大圖 ×</button><img alt=""><p></p></dialog>
<div class="toast" role="status" aria-live="polite" hidden></div></body></html>'''


def figure(l):
    t = l['tutorial']
    return f'''<figure class="lesson-figure"><button type="button" class="image-zoom" aria-label="放大本課操作圖"><img src="static/images/{h(t['image'])}" alt="{h(t['caption'])}"></button><figcaption>{h(t['caption'])}<span>點圖可放大</span></figcaption></figure>'''


def concept(l):
    i = l['id']
    flows = {
        1: [('編程員', '拼積木與保存'), ('操作員', '核對 MAC 與停止'), ('記錄員', '觀察與留下證據')],
        2: [('掃描', '尋找同網段設備'), ('核對', '完整 MAC 對標籤'), ('連線', '查看狀態與電量')],
        3: [('站立', '先準備姿勢'), ('前進 1 秒', '短時限移動'), ('停止', '取消速度'), ('趴下', '結束任務')],
        4: [('保持相同', '速度、地面、起點'), ('只改一項', '前進秒數'), ('比較證據', '停止後量距離')],
        5: [('先找前方', '以狗的朝向判斷'), ('再找左右', '站到狗後方核對'), ('停止後看', '比較實際方向')],
        6: [('迴圈外', '站立一次'), ('重複 2 次', '前進 + 等待'), ('迴圈後', '停止')],
        7: [('設定', 't = 0.5'), ('第 1 次讀取', '前進 t 秒'), ('第 2 次讀取', '前進 t 秒')],
        8: [('條件', 'n == 1？'), ('成立', '左轉 15 度'), ('不成立', '右轉 15 度')],
        9: [('積木', '修改參數'), ('Python', '讀懂對應文字'), ('手動改文字後', '不會反向更新積木')],
        10: [('看提示', '先找錯誤行'), ('改一處', '冒號、括號、縮排'), ('再練習', '比較修復前後')],
        11: [('訓練圖片', '每類約 20–30 張起步'), ('變化', '角度 / 背景 / 距離'), ('另留測試', '每類至少 5 張')],
        12: [('三類圖片', '左轉卡 / 停止卡 / 其他'), ('訓練', '核對樣本與類別'), ('匯出', 'TensorFlow.js ZIP')],
        13: [('信心分數', '一次分類的模型分數'), ('測試正確率', '答對張數 ÷ 測試總張數'), ('公平比較', '兩版測同一批新圖')],
        14: [('完整 ZIP', '模型 + 類別 + 權重'), ('靜態測試', '先看類別與分數'), ('作品資料夾', '專案 + 模型 + 記錄')],
        15: [('最多等 5 秒', '連續 3 張新畫面 ≥ 0.80'), ('確認左轉卡', '只左轉一次'), ('超時', '跳過左轉，最後停止')],
        16: [('作品', '有明確結束與停止'), ('證據', '兩次可比較的測試'), ('解釋', '每個人說清一段')]
    }
    return '<div class="concept-flow" aria-label="本課概念關係">' + ''.join(
        f'<div><strong>{h(a)}</strong><span>{h(b)}</span></div>' for a, b in flows[i]) + '</div>'


def record_table(l, editable=True):
    if l['id'] == 13:
        headers = ['圖片 / 真實類', 'v1 預測 / 分數', 'v2 預測 / 分數']
        rows = [f'{label} {i}' for label in ['左轉卡', '停止卡', '其他'] for i in range(1, 6)]
    else:
        headers, rows = l['record'], l['rows']
    cells = ''
    for n, row in enumerate(rows):
        inputs = ''.join(f'<td><textarea rows="2" data-field="record-{n}-{j}" aria-label="{h(row)}：{h(col)}"></textarea></td>' if editable else '<td></td>' for j, col in enumerate(headers[1:], 1))
        cells += f'<tr><th scope="row">{h(row)}</th>{inputs}</tr>'
    return '<div class="table-wrap"><table class="record-table"><thead><tr>' + ''.join(f'<th scope="col">{h(x)}</th>' for x in headers) + '</tr></thead><tbody>' + cells + '</tbody></table></div>'


def lesson_page(l):
    i, t = l['id'], l['tutorial']
    objectives = ''.join(f'<li>{h(x)}</li>' for x in l['goals'])
    checks = ''.join(f'<label class="check-row"><input type="checkbox" data-field="check-{n}">{h(x)}</label>' for n, x in enumerate(l['check']))
    steps = ''.join(f'<li class="step"><span class="step-number">{n+1:02}</span><div><p>{h(s)}</p><div class="expected"><strong>核對</strong>{h(e)}</div></div></li>' for n, (s, e) in enumerate(zip(l['steps'], l['expected'])))
    questions = ''.join(f'<div class="reflection"><label for="answer-{n}"><span>{["預測","解釋","改進"][n]}</span>{h(q)}</label><textarea id="answer-{n}" rows="3" data-field="answer-{n}" placeholder="寫下你的想法與證據。"></textarea></div>' for n, q in enumerate(l['questions']))
    answers = ''.join(f'<li><strong>{h(q)}</strong><p>{h(a)}</p></li>' for q, a in zip(l['questions'], l['answers']))
    previous = link(lesson_name(i-1), '← 上一課') if i > 1 else link('../使用說明.html#courses', '← 課程地圖')
    following = link(lesson_name(i+1), '下一課 →', 'button primary') if i < 16 else link('../使用說明.html#courses', '回課程地圖', 'button primary')
    network = '<p class="notice network">本課自主訓練需要網路。課前先開啟網站；無法使用時按教師備案完成模型測試，自主訓練另行補做。</p>' if i == 12 else ''
    external = '<p>'+link('https://teachablemachine.withgoogle.com/', '開啟 Teachable Machine ↗', 'button', target='_blank', rel='noopener')+'</p>' if i == 12 else ''
    if i == 11:
        external = '<p>'+link('../列印資料/操作與試教記錄.pdf#page=5','列印課堂色卡','button')+'</p><p class="record-reminder">使用自己的實拍圖片訓練。配套示例圖片只用來練習操作，不當作真實場景測試證據。</p>'
    save_note = '本頁不依賴電腦自動保存。換頁、關閉或學校電腦還原前，請匯出記錄到老師指定的持久位置；模型需另存。'
    project_data = json.dumps({'format':'d1-classroom','version':1,'blocks':l['blocks'],'python':l['code'],'edited':bool(l.get('codeOnly')),'mode':'python' if l.get('codeOnly') else 'blocks','lesson':i},ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    content = f'''<div class="breadcrumb">{link('../使用說明.html#courses','課程地圖')}<span>/</span>第 {i:02} 課</div>
<header class="lesson-heading"><div><p class="eyebrow">{h(l['area'])}學習 <span>第 {i:02} 課 / 16</span></p><h1>{h(l['title'])}</h1><p class="lead">{h(t['headline'])}</p></div><div class="lesson-tools"><span class="tag">{h(t['tag'])}</span><span>45 分鐘</span><button type="button" class="button" id="projection" aria-pressed="false">投影閱讀</button></div></header>
{network}<nav class="lesson-tabs" aria-label="本課章節">{''.join(f'<button type="button" data-stage="{n}" aria-controls="stage-{n}" aria-pressed="{str(n==0).lower()}"><span>0{n+1}</span>{label}</button>' for n, label in enumerate(['讀懂任務','動手做','修改與測試','回顧與保存']))}</nav>
<section id="stage-0" class="lesson-panel" data-panel="0" aria-label="讀懂任務"><div class="mission-layout"><div class="mission-copy"><p class="eyebrow">今天的任務</p><h2>{h(t['headline'])}</h2><p>{h(l['scene'])}</p><h3>完成時，你能做到</h3><ul class="goals">{objectives}</ul><p class="why">{h(t['why'])}</p></div>{figure(l)}</div><div class="key-concept"><h3>先理解一件事</h3><p>{h(l['term'])}</p>{concept(l)}</div></section>
<section id="stage-1" class="lesson-panel" data-panel="1" aria-label="動手做" hidden><div class="section-intro"><p class="eyebrow">一步一步核對</p><h2>跟著做，看到結果再往下。</h2><p>準備：{h(l['materials'])}</p></div><div class="download-row"><button type="button" class="button primary" id="download-project">下載本課起步專案</button><button type="button" class="button" id="download-python">下載 Python 參考</button><span>也可在學生工坊選本課，再按「載入」。</span></div><ol class="steps">{steps}</ol>{external}<details class="code-reference"><summary>查看本課 Python 參考</summary><pre><code>{h(l['code'].strip())}</code></pre><p>這段程式在學生工坊執行；先保持練習模式。</p></details><aside class="notice">實機前：核對本組完整 MAC、電量至少 30%、場地淨空，取得老師示意。運行後仍須目視確認停止。</aside></section>
<section id="stage-2" class="lesson-panel" data-panel="2" aria-label="修改與測試" hidden><div class="section-intro"><p class="eyebrow">一次只改一項</p><h2>先寫預測，再記錄觀察。</h2></div><div class="practice-grid"><section><span class="section-number">必做</span><h3>先完成原任務</h3><p>{h(l['follow'])}</p></section><section><span class="section-number">修改</span><h3>只改這一項</h3><p>{h(l['change'])}</p></section></div><label class="field-label" for="prediction">這次改了什麼？你預計會發生什麼？</label><textarea id="prediction" data-field="prediction" rows="3" placeholder="修改項目 / 預測 / 比較時保持相同的條件"></textarea><h3>我的測試記錄</h3>{record_table(l)}<details class="challenge"><summary>完成後再挑戰</summary><p>{h(l['challenge'])}</p></details><p class="record-reminder">{save_note}</p></section>
<section id="stage-3" class="lesson-panel" data-panel="3" aria-label="回顧與保存" hidden><div class="section-intro"><p class="eyebrow">讓想法有證據</p><h2>說清楚你做了什麼。</h2></div><div class="reflection-grid">{questions}</div><section class="completion"><h3>完成檢查</h3>{checks}<label class="field-label" for="exit">退出題：{h(l['exit'])}</label><textarea id="exit" data-field="exit" rows="2"></textarea></section><div class="record-actions"><button type="button" class="button primary" id="export-record">匯出本課記錄</button><label class="button file-button">匯入記錄<input type="file" id="import-record" accept=".json,application/json"></label>{link('../列印資料/課堂工作紙.pdf','開啟可列印工作紙','button')}<button type="button" class="button" id="print-lesson">列印本課教程</button></div><p class="record-reminder">{save_note}</p><p>學生工坊另按「保存專案」；AI 作品同時保存模型 ZIP、測試圖片與本課記錄。</p></section>
<footer class="stage-footer"><span id="stage-count" aria-live="polite">第 1 段，共 4 段</span><div><button type="button" class="button" id="previous-stage" disabled>上一段</button><button type="button" class="button primary" id="next-stage">下一段 →</button></div></footer>
<details class="teacher-notes"><summary>教師提示與參考答案</summary><div class="teacher-note-grid"><section><h3>常見卡點</h3><p>{h(l['error'])}</p></section><section><h3>設備或網路未就緒</h3><p>{h(l['fallback'])}</p></section></div><h3>提問與參考</h3><ol class="answer-list">{answers}</ol><p>45 分鐘節奏：5 分鐘情境與分工 → 5 分鐘預測 → 15 分鐘跟做 → 15 分鐘修改與測試 → 5 分鐘保存回顧。</p></details>
<nav class="adjacent-lessons" aria-label="相鄰課程">{previous}{following}</nav>'''
    content+='<script type="application/json" id="project-data">'+project_data+'</script>'
    return page(l['title'], content, lesson=i)


def home_page():
    groups = ''
    for label, name, description, ids in GROUPS:
        cards = ''
        for i in ids:
            l = LESSONS[i-1]
            cards += f'''<a class="course-card" href="教程/{lesson_name(i)}"><span class="course-number">{i:02}</span><div><span class="course-area">{h(l['area'])} / {h(l['tutorial']['tag'])}</span><h3>{h(l['title'])}</h3><p>{h(l['tutorial']['why'])}</p></div><span class="course-arrow" aria-hidden="true">↗</span></a>'''
        groups += f'<section class="course-group"><header><span class="group-number">{label}</span><div><h2>{name}</h2><p>{description}</p></div></header><div class="course-grid">{cards}</div></section>'
    content = f'''<section class="home-hero"><div><p class="eyebrow">D1 EDU · 初中科技與人工智能</p><h1>從第一個指令，<br>到會看圖的機器狗。</h1><p class="hero-description">16 堂動手做的課。用積木建立思路，用 Python 表達想法，再用自己的圖片訓練模型。</p><div class="hero-actions">{link('教程/lesson-01.html','開始第 1 課 →','button primary')}{link('教程/start.html','第一次使用','button')}</div><p class="hero-meta">每課 45 分鐘 · 每組 3 人 · 教程可離線開啟</p></div><figure><img src="教程/static/images/robot-0.jpg" alt="D1 Edu 四足機器狗原廠產品圖"><figcaption>認識設備 → 編寫程式 → 測試與改進</figcaption></figure></section>
<section class="entry-row" aria-label="使用入口"><a href="教程/start.html"><span>學生</span><strong>開啟工具，開始練習</strong><p>掃描 MAC、保存專案、重開作品。</p></a><a href="教程/teacher.html"><span>教師</span><strong>照著節奏，帶好一堂課</strong><p>課前檢查、輪次安排、提問與評量。</p></a><a href="教程/deploy.html"><span>技術人員</span><strong>同一份腳本，逐隻初始化</strong><p>原廠 SDK 已附，部署與驗收有清單。</p></a></section>
<section id="courses" class="course-map"><div class="section-heading"><p class="eyebrow">學習路線</p><h2>一步一步，把作品做完整。</h2><p>所有課程均可直接開啟。先完成本課必做，再嘗試延伸挑戰。</p></div>{groups}</section>
<section class="resources"><div><p class="eyebrow">帶到課堂</p><h2>同一套內容，兩種閱讀方式。</h2><p>網頁跟做與投影共用一份教程；列印資料用來記錄、帶課與現場驗收。</p></div><div class="resource-links">{link('列印資料/課堂工作紙.pdf','學生工作紙 · 16 課')}{link('列印資料/教師帶課手冊.pdf','教師帶課手冊')}{link('列印資料/操作與試教記錄.pdf','操作卡、試教表與色卡')}{link('配套檔案/備用色卡模型.zip','備用模型 ZIP',download='')}{link('配套檔案/課程專案/','課程專案資料夾')}</div></section>
<aside class="release-note"><strong>開始上課前</strong><p>教程與工具可離線使用；第 12 課自主訓練需要網站與網路。真機的初始化、動作與停止效果需先完成現場驗收，未驗收時使用練習模式。</p></aside>'''
    return page('課程首頁', content, root=True)


def guide(title, subtitle, sections):
    nav = ''.join(f'<a href="#{key}">{h(heading)}</a>' for key, heading, _ in sections)
    body = ''.join(f'<section id="{key}" class="guide-section"><h2>{h(heading)}</h2>{content}</section>' for key, heading, content in sections)
    return page(title, f'<div class="breadcrumb">{link("../使用說明.html","課程首頁")}<span>/</span>{h(title)}</div><header class="guide-heading"><p class="eyebrow">D1 機器狗實驗室</p><h1>{h(title)}</h1><p class="lead">{h(subtitle)}</p></header><div class="guide-layout"><nav class="guide-toc" aria-label="本頁目錄">{nav}</nav><article class="guide-content">{body}</article></div>')


def start_page():
    return guide('學生開始', '每次上課，都從相同的四件事開始。', [
        ('open', '01 開啟工具', '<p>先完整解壓套件到老師指定的資料夾，雙擊根目錄的 <strong>啟動學生工坊.cmd</strong>。也可開啟「學生工具 / D1學生工坊 / D1學生工坊.exe」。不要只複製 EXE。</p><p>程式啟動不需要安裝 Node.js 或 Python。保持「練習模式」，選第 3 課 → 載入 → 運行，看到「程序完成」即完成第一次軟體練習。</p><figure class="wide-figure"><button class="image-zoom" type="button"><img src="static/images/workshop-current.png" alt="新版學生工坊主畫面，顯示課程選擇、積木、相機和運行記錄。"></button><figcaption>實際學生工坊介面；點圖放大。</figcaption></figure>'),
        ('connect', '02 連上自己的狗', '<ol><li>電腦與狗加入同一個可互通的課室網路。</li><li>點「掃描機器狗」，核對狗身標籤上的<strong>完整 Wi-Fi MAC</strong>。</li><li>在同一列點「連線」，再次核對畫面 MAC 與電量。</li><li>先保持練習模式；老師確認場地後，才切換實機測試。</li></ol><p>MAC 用來辨認機身；它不是密碼。一隻狗同時由一台電腦控制，使用中的狗不能搶連。電腦重啟還原後重新掃描即可，沒有首次配對步驟。</p><figure class="wide-figure"><button class="image-zoom" type="button"><img src="static/images/scan-current.png" alt="依完整 MAC 選擇機器狗的實際掃描清單。"></button><figcaption>假 SDK 掃描示例；測試 MAC 不代表現場設備。</figcaption></figure>'),
        ('practice', '03 先練習，再實機', '<p>練習模式會列出指令，協助核對順序與參數；它不模擬距離、姿勢或碰撞。練習畫面的電量也不是實體設備電量。</p><p>實機前核對本組 MAC、電量至少 30%、場地淨空，操作員守著停止按鈕，等待老師示意。實機結束後目視確認停止；停止未確認時，通知老師並保持距離。</p><p>課件頁面不會控制機器狗。程式在 Windows 學生工坊執行，運行期間電腦需保持與狗連線。</p>'),
        ('save', '04 保存能帶走的作品', '<div class="folder-tree"><code>第03課_03組/<br>├─ 第03課_03組_v1.d1.json<br>├─ 模型_v1.zip（AI 課使用）<br>├─ 測試圖片/<br>└─ 第03課_學習記錄.json</code></div><p>在學生工坊按「保存專案」保存積木與 Python。模型不在專案裡，重開作品後需另外匯入模型 ZIP。教程的文字與表格請按「匯出本課記錄」保存，下次可匯入。</p><p>學校電腦會重啟還原時，請存到老師指定的網路磁碟、USB 或其他可保留的位置。下課先停止、目視確認、斷開，再保存與收拾。</p>'),
        ('help', '遇到問題，先看這裡', '<div class="help-list"><details><summary>掃不到機器狗</summary><p>確認電源、Wi-Fi 與橋接服務。隔離網路、不同 IPv4 網段或封鎖廣播的 Wi-Fi 不能自動發現，交由老師或技術人員處理。</p></details><details><summary>顯示使用中</summary><p>先核對是否選錯狗；由原連線者停止並斷開，再重新掃描。不要多組反覆搶連。</p></details><details><summary>模型載入失敗</summary><p>選完整 TensorFlow.js ZIP，包含 model.json、metadata.json 與權重 .bin。若缺檔，回網站重新下載完整 ZIP。</p></details><details><summary>改了 Python，積木沒有改</summary><p>文字不會反向轉換成積木。切到 Python 或雙視圖運行文字；「用積木更新 Python」會覆蓋手動文字，先保存。</p></details></div>')])


def teacher_page():
    rows = ''.join(f'<tr><th>{l["id"]:02} {h(l["title"])}</th><td>{h(l["goals"][0])}</td><td>{h("；".join(l["check"]))}</td><td>{link(lesson_name(l["id"]),"開啟本課")}</td></tr>' for l in LESSONS)
    return guide('教師帶課', '先建立同一套課堂習慣，再逐課加入新概念。', [
        ('before','課前 10 分鐘','<ul><li>技術人員已完成該批狗的現場驗收；確認現場硬體停止方式及等待區。</li><li>每組一台 Windows 電腦、一隻狗、三個角色。核對機身完整 MAC 標籤與電量。</li><li>開啟本課教程與起步專案，先做一次練習；本課工作紙按需列印。</li><li>第 11–15 課核對相機、模型及測試圖片；第 12 課預先開網站並確認網路。</li><li>老師先示範停止流程、保存位置和輪次安排。</li></ul>'),
        ('rhythm','45 分鐘帶課節奏','<ol class="timeline"><li><strong>0–5 分鐘</strong>情境、分工與停止檢查。</li><li><strong>5–10 分鐘</strong>讀任務、先預測，不立即公布答案。</li><li><strong>10–25 分鐘</strong>示範一小步，學生跟做並核對結果。</li><li><strong>25–40 分鐘</strong>完成必做、只改一項，留下比較記錄。</li><li><strong>40–45 分鐘</strong>停止與保存，每人回答退出題。</li></ol><p>AI 的採集、訓練與改進可延至下一課，不為趕進度省略測試。教師提示和參考答案放在每課底部，可自行展開。</p>'),
        ('roles','三人分工與實機輪次','<div class="concept-flow"><div><strong>編程員</strong><span>拼程式、改一項、保存</span></div><div><strong>操作員</strong><span>核對 MAC、守著停止</span></div><div><strong>記錄員</strong><span>預測、觀察、記錄</span></div></div><p>每課輪換角色。早期只開放一組實機運動，其餘組做練習與記錄；多組同時運動須在場地、停止流程與網路負載驗收通過後逐步增加。每次短測後回等待區，禁止臨時加入未測長動作。</p>'),
        ('assessment','評量看得見的證據','<div class="table-wrap"><table><thead><tr><th>觀察項目</th><th>達成的證據</th></tr></thead><tbody><tr><td>程式邏輯</td><td>能指出順序、變數或分支，解釋執行結果。</td></tr><tr><td>測試方法</td><td>先預測、只改一項，留下至少兩筆可比較記錄。</td></tr><tr><td>操作習慣</td><td>核對 MAC、等待示意、目視確認停止、保存作品。</td></tr><tr><td>個人理解</td><td>每個學生能解釋自己的修改或資料。</td></tr></tbody></table></div><p>用「已能獨立完成 / 提示後完成 / 仍需補做」記錄。設備失敗時，邏輯與紙上測試可分別評量；實機操作和自主訓練如未發生，明確記為待補做。</p>'),
        ('lessons','16 課備課索引',f'<div class="table-wrap"><table class="teacher-index"><thead><tr><th>課程</th><th>本課重點</th><th>完成證據</th><th>教程</th></tr></thead><tbody>{rows}</tbody></table></div>'),
        ('backup','斷網、缺設備與試教','<p>動作課用練習記錄和指令卡研究邏輯；採集課用示例圖片規劃樣本；訓練網站不可用時，先匯入配套備用模型做分類測試，並記錄模型來源，自主訓練另行補做。備用模型不是學生自己的成果。</p><p>第一次帶課前，老師完整試帶第 3 課與第 15 課，演練「使用中」「網路中斷」「停止未確認」，並填寫操作與試教記錄。每次試教記一個真實卡點和下一次改法。</p><div class="download-row">'+link('../列印資料/教師帶課手冊.pdf','列印教師手冊','button')+link('../列印資料/操作與試教記錄.pdf','現場驗收、試教與色卡','button')+'</div>')])


def deploy_page():
    return guide('設備部署', '技術人員做一次，學生每堂課只需掃描與核對。', [
        ('network','01 先準備可互通的網路','<p>路由器用 DHCP 即可。電腦與狗需在同一個可互通、允許廣播的 IPv4 網段；關閉用戶端隔離。允許 UDP 8765 掃描、TCP 8765 控制、TCP 8554 RTSP，不對外轉發。</p><p>機身使用穩定 Wi-Fi MAC，不啟用隨機 MAC；更換網卡後重貼標籤。MAC 只負責辨識，不需要學生輸入 IP、人工設備 ID 或配對碼。</p>'),
        ('install','02 每隻狗執行同一份腳本','<p>初始化包已含原廠 SDK V2.0.7 完整原包與 BSD 授權。先確認實體是相容的 zsl-1 高層介面機型、韌體與 Linux CPython 3.10 環境。第一次部署先核對原廠允許的機載 SDK 配置與硬體停止方式。</p><p>從解壓後的完整套件資料夾開啟 PowerShell，把「機器狗IP」換成本次 DHCP 地址；登入帳戶不同時替換 firefly。</p><pre><code>scp ".\\技術人員部署\\d1-setup.zip" firefly@機器狗IP:~/d1-setup.zip\nssh firefly@機器狗IP</code></pre><p>登入機器狗後：</p><pre><code>unzip -o ~/d1-setup.zip -d ~/\ncd ~/d1-setup\nsudo bash install.sh</code></pre><p>腳本檢查架構、Python、Wi-Fi、SDK 雜湊與匯入，安裝橋接及 systemd。只有就緒檢查通過才顯示初始化成功、完整 MAC 與開機自啟狀態。</p><p>把 <code>/opt/d1-classroom/機身標籤.txt</code> 裡的完整 Wi-Fi MAC 貼到狗身。每隻狗用相同腳本，學生電腦不安裝 SDK。</p>'),
        ('service','03 重開機並核對服務','<pre><code>systemctl status d1-classroom\njournalctl -u d1-classroom -n 50 --no-pager</code></pre><p>重開機後重新掃描，確認同一 MAC 可連線。程式、AI 推論與相機解碼在 Windows 執行，運行期間需保持連線；這不是把學生程式刷入狗內自主運行。</p><p>橋接預設 SDK 機內地址為 127.0.0.1。韌體若要求其他配置，先按完整技術文件核對；不要猜測或任意改原廠運動服務。需要動態綁定 Wi-Fi IP 時，技術文件提供 <code>--sdk-address auto</code>。</p>'),
        ('accept','04 先一隻驗收，再擴到全班','<ol><li>掃描、完整 MAC、連線、電量與正常斷開。</li><li>重開工具、重啟還原電腦、換 DHCP 地址後重新掃描。</li><li>第二台電腦連同一狗應被拒絕，原使用者釋放後才能接手。</li><li>站立、停止、趴下，再做低速 0.5 秒前進與左右 15 度；記錄實際延遲。</li><li>運動中測停止、斷網、關閉工具與橋接故障；按已驗證的現場硬體停止流程處理。</li><li>相機與模型持續運行，再逐步增加同時使用的組數。</li></ol><p>軟體回覆接受停止，不能證明機身已靜止。未通過現場驗收前維持練習模式，填表保留設備 MAC、韌體、時間與觀察者。</p><div class="download-row">'+link('../技術人員部署/d1-setup.zip','下載完整初始化包','button',download='')+link('../技術人員部署/技術部署與實機驗收.md','完整技術文件','button')+link('../列印資料/操作與試教記錄.pdf','列印現場驗收表','button')+'</div>')])


def about_page():
    return guide('版本與資料來源', '清楚區分已完成的軟體檢查與仍需現場完成的工作。', [
        ('version','這份交付包含什麼',f'<p>{VERSION} / 2026-10-31：16 課離線網頁教程、三份列印文件、Windows x64 學生工坊、32 份起步 JSON / Python、三類示例圖片、備用模型、自帶原廠 SDK 的初始化包與原始碼。</p><p>本版全面採用 MAC 掃描連線。舊版 Word / PPT 與教材 PDF 已移到工作區的 references/歷史教材，不混入正式交付。</p>'),
        ('scope','驗收範圍','<p>本機驗證涵蓋課件導覽、離線檔案與下載、記錄匯入匯出、不同寬度排版、列印 PDF，以及學生工坊的練習、模型匯入與假 SDK 通訊流程。詳細結果見套件根目錄的驗收狀態.md。</p><p>沒有連接實體狗。本機測試與假 SDK 不能代替機身初始化、真實動作、停止延遲、相機與整班網路負載驗收。</p>'),
        ('sources','圖片、程式與外部工具','<ul><li>產品圖與機身示意：智元 D1 Edu 原廠產品資料；原圖保留來源權利。</li><li>積木、編輯器與模型畫面：配套學生工坊實際截圖。掃描畫面為假 SDK 範例，模型畫面的分數來自備用示例模型。</li><li>圖像訓練：'+link('https://teachablemachine.withgoogle.com/','Google Teachable Machine',target='_blank',rel='noopener')+'。網站入口於 2026-10-20 核對；操作圖片為先前核對的參考介面，網站可能更新。</li><li>模型介面參考：'+link('https://github.com/googlecreativelab/teachablemachine-community/tree/master/libraries/image','Google Creative Lab 官方圖像模型函式庫',target='_blank',rel='noopener')+'。學生工坊使用標準 224 × 224 彩色圖像模型與完整 TensorFlow.js ZIP。</li><li>原廠 SDK 原包、雜湊與 BSD 授權：技術人員部署/d1-setup.zip 裡的 sdk/。</li><li>工具第三方授權：學生工具/D1學生工坊/THIRD-PARTY-NOTICES.txt 及附帶授權檔。</li></ul>'),
        ('maintain','後續如何修改','<p>課程內容的唯一來源是原始碼裡的 curriculum/lessons.json。網頁、工作紙和教師資料都從它產生，版式在 courseware/，生成入口在 build/courseware.py 與 build/printables.py。</p><p>修改程式後先 bundle、package，再用 build/deliver.py 重建交付 ZIP 與 SHA-256。原始碼使用說明在技術人員部署目錄，完整原始碼 ZIP 位於套件根目錄。</p>')])


def build():
    assert [l['id'] for l in LESSONS] == list(range(1, 17))
    static = SITE / 'static'
    (static / 'images').mkdir(parents=True, exist_ok=True)
    for name in ['style.css', 'course.js']:
        shutil.copy2(R / 'courseware' / name, static / name)
    images = {l['tutorial']['image'] for l in LESSONS} | {'robot-0.jpg', 'workshop-current.png', 'scan-current.png'}
    for name in images:
        source = R / 'assets' / name
        if not source.is_file():
            raise SystemExit(f'缺少新版操作圖：{source}；請先執行 build/capture-courseware.cjs')
        shutil.copy2(source, static / 'images' / name)
    write('使用說明.html', home_page())
    for l in LESSONS:
        write('教程/' + lesson_name(l['id']), lesson_page(l))
    for name, builder in [('start', start_page), ('teacher', teacher_page), ('deploy', deploy_page), ('about', about_page)]:
        write('教程/' + name + '.html', builder())
    (OUT / '配套檔案' / '課程專案').mkdir(parents=True, exist_ok=True)
    shutil.copytree(R / 'curriculum' / 'projects', OUT / '配套檔案' / '課程專案', dirs_exist_ok=True)
    shutil.copytree(R / 'curriculum' / 'samples', OUT / '配套檔案' / '色卡示例圖片', dirs_exist_ok=True)
    for name in ['備用色卡模型.zip', '備用模型說明.txt']:
        shutil.copy2(R / 'curriculum' / name, OUT / '配套檔案' / name)
    write('啟動學生工坊.cmd', '@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\nstart "" "學生工具\\D1學生工坊\\D1學生工坊.exe"\n')
    print('Built course home, 16 lessons, 4 guides, local assets and classroom projects.')


if __name__ == '__main__':
    build()
