"""Three concise, printable companions to the canonical offline course."""
from pathlib import Path
from html import escape
import json
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4

R = Path(__file__).resolve().parents[1]
OUT = R.parent / 'output/D1彩色課程套件/列印資料'
LESSONS = json.loads((R / 'curriculum/lessons.json').read_text(encoding='utf-8'))
W, H = A4
M = 44
INK, MUTED, BLUE, LINE, TINT = map(HexColor, ['#182d47', '#52657b', '#245bb5', '#cdd9e8', '#edf4ff'])
pdfmetrics.registerFont(TTFont('D1', os.environ.get('D1_FONT', 'C:/Windows/Fonts/msjh.ttc'), subfontIndex=0))
pdfmetrics.registerFont(TTFont('D1B', os.environ.get('D1_FONT_BOLD', 'C:/Windows/Fonts/msjhbd.ttc'), subfontIndex=0))
pdfmetrics.registerFontFamily('D1', normal='D1', bold='D1B', italic='D1', boldItalic='D1B')
STYLES = {}


def para(text, size=11, color=INK, bold=False):
    text = text.replace('–','-').replace('—','-').replace('‑','-')
    key = (size, str(color), bold)
    if key not in STYLES:
        STYLES[key] = ParagraphStyle(str(key), fontName='D1B' if bold else 'D1', fontSize=size,
                                    leading=size * 1.65, textColor=color, wordWrap='CJK', spaceAfter=0)
    return Paragraph(escape(text).replace('\n', '<br/>'), STYLES[key])


def text(c, value, x, y, width=W-2*M, size=11, color=INK, bold=False):
    p = para(value, size, color, bold)
    _, height = p.wrap(width, 1000)
    p.drawOn(c, x, y-height)
    return y-height


def start(c, label, page):
    c.setFillColor(INK); c.setFont('D1B', 16); c.drawString(M, H-36, 'D1')
    c.setFont('D1', 9); c.drawString(M+35, H-34, '機器狗實驗室')
    c.setFillColor(MUTED); c.setFont('D1', 9); c.drawRightString(W-M, H-34, label)
    c.setStrokeColor(LINE); c.setLineWidth(.6); c.line(M, H-47, W-M, H-47)
    c.setFillColor(MUTED); c.setFont('D1', 8.5)
    c.drawString(M, 25, '課程套件 2.0.0 | 2026-10-21')
    c.drawRightString(W-M, 25, f'{page:02}')
    return H-67


def section(c, label, y):
    return text(c, label, M, y, size=12, color=BLUE, bold=True)-7


def lines(c, y, count=2, spacing=23):
    c.setStrokeColor(LINE); c.setLineWidth(.5)
    for _ in range(count):
        y -= spacing; c.line(M, y, W-M, y)
    return y-15


def table(c, headers, rows, y, heights=None, widths=None, compact=False):
    widths = widths or [(W-2*M)/len(headers)]*len(headers)
    data = [[para(x, 9.5, bold=True) for x in headers]]
    data += [[para(str(x), 9 if compact else 10) for x in row] for row in rows]
    heights = heights or [33] + [43]*len(rows)
    t = Table(data, colWidths=widths, rowHeights=heights)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TINT), ('LINEBELOW', (0,0), (-1,0), .7, LINE),
        ('LINEBELOW', (0,1), (-1,-1), .4, LINE), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 9), ('RIGHTPADDING', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 3 if compact else 5), ('BOTTOMPADDING', (0,0), (-1,-1), 3 if compact else 5)]))
    _, height = t.wrap(W-2*M, 1000); t.drawOn(c, M, y-height)
    return y-height-17


def finish(c, y, context):
    if y < 43:
        raise ValueError(f'Page overflow: {context} ends at {y:.1f}')
    c.showPage()


def make_canvas(name, title):
    OUT.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT/name), pagesize=A4, pageCompression=1)
    c.setTitle(title); c.setAuthor('D1 課程設計'); c.setSubject('D1 課程套件 2.0.0')
    return c


def worksheets():
    c = make_canvas('課堂工作紙.pdf', 'D1 16 課課堂工作紙')
    for l in LESSONS:
        y = start(c, '學生工作紙 / 45 分鐘', l['id'])
        y = text(c, f'第 {l["id"]:02} 課  {l["title"]}', M, y, size=23, bold=True)-5
        y = text(c, l['tutorial']['headline'], M, y, size=11.5, color=MUTED)-14
        y = text(c, '班級：________  組別：______  姓名：____________  日期：________', M, y, size=10)-12
        if l['id'] != 13:
            y = section(c, '01 / 先預測', y)
            y = text(c, l['questions'][0], M, y, size=11)
            y = lines(c, y, 2, 22)
        y = section(c, ('01' if l['id']==13 else '02')+' / 我的測試記錄', y)
        if l['id'] == 13:
            y = text(c, '同一批 15 張圖片不參加訓練；每格記「預測類 / 分數 / 對錯」。', M, y, size=9.5, color=MUTED)-8
            rows = [[f'{label} {i}', '', ''] for label in ['左轉卡','停止卡','其他'] for i in range(1,6)]
            y = table(c, ['真實類別 / 編號','v1','v2'], rows, y, [28]+[22]*15, [140,183,184], compact=True)
            y = text(c, 'v1 正確 ____ / 15 = ____ %    v2 正確 ____ / 15 = ____ %', M, y, size=10)-12
        else:
            y = text(c, '修改了什麼：________________________________________________', M, y, size=10)-11
            rows = [[row, '', ''] for row in l['rows']]
            y = table(c, l['record'], rows, y, widths=[145,181,181])
        y = section(c, ('02' if l['id']==13 else '03')+' / 用證據說明', y)
        y = text(c, l['questions'][1] if l['id'] != 13 else '新增了哪些訓練情境？同一批測試圖的結果有何變化？', M, y, size=11)
        y = lines(c, y, 2 if l['id'] != 13 else 1, 22)
        y = section(c, '完成檢查', y)
        for item in l['check']:
            c.setStrokeColor(MUTED); c.rect(M, y-11, 8, 8, fill=0, stroke=1)
            y = text(c, item, M+17, y, width=W-2*M-17, size=10)-7
        y -= 2
        y = text(c, '保存：學生工坊專案 + 本課記錄；AI 課另存模型 ZIP 與測試圖片。', M, y, size=9, color=MUTED)
        finish(c, y, f'worksheet {l["id"]}')
    c.save()


def teacher_manual():
    c = make_canvas('教師帶課手冊.pdf', 'D1 教師帶課手冊')
    y = start(c, '教師帶課 / 共 18 頁', 1)
    y = text(c, '把每一堂課，\n帶成一次小實驗。', M, y, size=27, bold=True)-18
    y = text(c, '16 課 × 45 分鐘 | 每組 3 人 | 積木、Python 與圖像分類', M, y, size=12, color=MUTED)-23
    for heading, value in [
        ('課前先核對','設備已通過現場驗收；每隻狗有完整 Wi-Fi MAC 標籤；場地、停止方式、電量和保存位置清楚。AI 課先試相機與模型，第 12 課先試網站。'),
        ('同一套課堂習慣','先預測 → 先練習 → 老師示意後短測 → 目視確認停止 → 保存與解釋。練習模式只列指令，不模擬物理移動。'),
        ('三個角色，每課輪換','編程員：程式與保存。操作員：核對 MAC、守著停止。記錄員：觀察場地、寫預測和數據。每個人都要能解釋一段。'),
        ('實機輪次','早期一次只開放一組運動，其他組練習與記錄。整班同時操作須先通過場地、停止流程與網路負載驗收。'),
        ('電腦會還原時','作品存到老師指定的持久位置。專案不含模型；教程文字記錄須匯出 JSON。不要依賴關機後仍會保留本機資料。')]:
        y = section(c, heading, y);y = text(c, value, M, y, size=11)-19
    finish(c, y, 'teacher intro')
    y = start(c, '課程節奏與評量', 2)
    y = text(c, '有節奏，也有證據。', M, y, size=23, bold=True)-20
    y = table(c, ['時間','課堂活動','老師觀察'], [
        ['0–5 分鐘','情境、分工與停止','每個角色是否就位'],['5–10 分鐘','讀任務、寫預測','先想過，再看結果'],['10–25 分鐘','示範與跟做','每一步核對預期結果'],['25–40 分鐘','修改、測試、記錄','只改一項；留下可比較證據'],['40–45 分鐘','保存、退出題','每個人能解釋自己的學習']], y, [32]+[39]*5, [87,180,240])
    y = section(c, '評量的四個觀察點', y)
    for value in ['程式邏輯：能解釋順序、參數、變數或分支。','測試方法：先預測、只改一項，至少兩筆可比較的記錄。','操作習慣：核對 MAC、等示意、確認停止、保存檔案。','個人理解：每人說明一項貢獻或一次修改。']:
        y = text(c, '• '+value, M, y, size=11)-9
    y = section(c, '設備或網路未就緒', y-9)
    y = text(c, '用練習記錄、指令卡或示例模型完成邏輯與測試活動。沒有發生的實機操作和自主訓練，明確標為待補做。備用模型標示來源，不能當作學生自訓成果。', M, y, size=11)-16
    y = text(c, '本手冊與教程同源。完整操作圖、步驟及起步檔案，見離線教程的對應課程；每課頁面下方可展開教師提示。', M, y, size=10, color=MUTED)
    finish(c, y, 'teacher rhythm')
    for l in LESSONS:
        y = start(c, f'第 {l["id"]:02} 課 / 教師備課', l['id']+2)
        y = text(c, l['title'], M, y, size=24, bold=True)-6
        y = text(c, l['tutorial']['headline'], M, y, size=12, color=MUTED)-15
        y = section(c, '準備與完成判據', y)
        y = text(c, l['materials'], M, y, size=10.5)-8
        y = text(c, '；'.join(l['check']), M, y, size=10.5)-15
        y = section(c, '示範時核對四步', y)
        for n, (step, expected) in enumerate(zip(l['steps'],l['expected']),1):
            y = text(c, f'{n}. {step}', M, y, size=10.5)-3
            y = text(c, '核對：'+expected, M+15, y, width=W-2*M-15, size=9.5, color=MUTED)-8
        y = section(c, '提問與參考答案', y-5)
        for question, answer in zip(l['questions'],l['answers']):
            y = text(c, question, M, y, size=10, bold=True)-2
            y = text(c, answer, M, y, size=9.5, color=MUTED)-8
        y = section(c, '卡點與備案', y-3)
        y = text(c, l['error'], M, y, size=9.5)-6
        y = text(c, l['fallback'], M, y, size=9.5, color=MUTED)
        finish(c, y, f'teacher {l["id"]}')
    c.save()


def operations():
    c = make_canvas('操作與試教記錄.pdf', 'D1 操作與試教記錄')
    y = start(c, '快速操作卡', 1)
    y = text(c, '每次上課，都做這四步。', M, y, size=24, bold=True)-25
    for title, value in [
        ('01 / 開啟與練習','雙擊啟動學生工坊.cmd。選本課 → 載入 → 保持練習模式 → 運行。練習只記錄指令，不會讓機器狗動。'),
        ('02 / 掃描與核對','電腦與狗在同一個可互通的網路。掃描機器狗 → 核對完整 Wi-Fi MAC 標籤 → 點連線 → 再核對狀態與電量。'),
        ('03 / 短測與停止','電量至少 30%、場地無人，等老師示意再實機。操作員守著停止。正常結束或異常時點停止，並目視確認機身已停。停止未確認，通知老師並保持距離。'),
        ('04 / 保存與斷開','保存專案、匯出教程記錄；AI 課另存模型 ZIP 與測試圖片。確認停止後斷開，存到老師指定的持久位置。重開專案後另行匯入模型。')]:
        y = section(c, title, y);y = text(c, value, M, y, size=12)-29
    y = section(c, '常見卡點', y)
    y = text(c, '掃不到：先看電源、網路與橋接服務。使用中：由原使用者停止並斷開。模型失敗：重新匯出完整 TensorFlow.js ZIP。Python 改動：不會反向更新積木。', M, y, size=10.5)
    finish(c, y, 'operations')
    y = start(c, '單台設備現場驗收', 2)
    y = text(c, '先一隻驗收，再擴到全班。', M, y, size=22, bold=True)-18
    for value in ['完整 Wi-Fi MAC：________________________________________','型號 / 韌體：__________________  日期 / 時間：____________','驗收人：______________________  現場停止方式：__________']:
        y = text(c, value, M, y, size=10.5)-12
    rows = [[x,'',''] for x in ['初始化 / SDK 就緒 / 開機自啟','重開機後掃描、MAC 與電量','換 DHCP / 還原電腦後重連','第二台占用拒絕、釋放後接手','站立、停止、趴下','低速前進 0.5 秒 / 左右 15 度','運動中點停止 / 實際延遲','斷網、關閉工具、橋接故障','RTSP、分類持續運行']]
    y = table(c,['驗收項目','觀察 / 延遲 / 結果','通過 / 待修'],rows,y,[31]+[35]*9,[210,210,87])
    y = text(c, '未通過項目 / 處置：', M, y, size=10.5);y=lines(c,y,2)
    y = text(c, '軟體回覆不等於物理停止。未驗收前保持練習模式；故障測試需依原廠與現場已驗證的硬體停止流程進行。', M, y, size=9.5, color=MUTED)
    finish(c, y, 'acceptance')
    y = start(c, '整班網路與試教', 3)
    y = text(c, '把現場卡點，留成下一次改法。', M, y, size=22, bold=True)-18
    y = text(c, '課次 / 班級：_______________  教師：___________  日期：________', M, y, size=10.5)-14
    y = text(c, '網路 / 路由器：________________  電腦數：_____  機器狗數：_____', M, y, size=10.5)-18
    y = table(c,['檢查情境','觀察與結果'],[[x,''] for x in ['逐步增加同時連線組數','多組相機與模型持續運行','各組 MAC 核對與占用行為','輪次 / 等待區 / 現場停止','作品重開與保存位置']],y,[31]+[43]*5,[210,297])
    for label in ['學生卡住的具體步驟 / 用時','本次採用的調整與效果','下次只改哪一項 / 如何判斷改善']:
        y = section(c,label,y);y=lines(c,y,2,20)
    finish(c,y,'pilot')
    y = start(c, '成果展示評量', 4)
    y = text(c, '每個人，都說清楚一段。', M, y, size=24, bold=True)-18
    y = text(c,'組別：_______  作品名稱：________________  版本：________',M,y,size=11)-18
    y = table(c,['觀察面向','具體證據','獨立 / 提示 / 待補'],[[x,'',''] for x in ['順序、參數或分支能解釋','先預測、一次只改一項','兩次可比較的測試記錄','核對 MAC、停止與保存','三人都能說明自己的貢獻']],y,[33]+[48]*5,[180,210,117])
    for label in ['一次有效修改與證據','每人的解釋 / 個人待練技能','下一步想改善什麼 / 判據']:
        y=section(c,label,y);y=lines(c,y,2,21)
    finish(c,y,'rubric')
    y = start(c, '可列印課堂色卡', 5)
    y = text(c, '先準備卡片，再採集真實照片。', M, y, size=22, bold=True)-18
    y = text(c, '使用彩色列印，沿外框剪下兩張卡片。第 11 課起變換背景、距離與角度，採集自己的訓練與測試圖片。', M, y, size=11)-20
    size = 210; bottom = y-size
    for x, color in [(M, '#285cb8'), (W-M-size, '#bd2638')]:
        c.setFillColor(HexColor(color)); c.rect(x,bottom,size,size,fill=1,stroke=0)
    c.setFillColor(HexColor('#ffffff'))
    center_x=M+size/2;center_y=bottom+size/2
    arrow=c.beginPath();arrow.moveTo(center_x-65,center_y);arrow.lineTo(center_x-15,center_y+50);arrow.lineTo(center_x-15,center_y+20);arrow.lineTo(center_x+65,center_y+20);arrow.lineTo(center_x+65,center_y-20);arrow.lineTo(center_x-15,center_y-20);arrow.lineTo(center_x-15,center_y-50);arrow.close();c.drawPath(arrow,fill=1,stroke=0)
    c.setFont('D1B',38);c.drawCentredString(W-M-size/2,center_y-14,'STOP')
    y = bottom-14
    text(c,'左轉卡',M,y,width=size,size=12,bold=True)
    text(c,'停止卡',W-M-size,y,width=size,size=12,bold=True)
    y -= 56
    y = section(c,'「其他」類要收集什麼？',y)
    y = text(c,'沒有卡片的桌面、不同背景和普通物品。不要只用一張固定灰卡代表其他；模型需要看過多種不該觸發的場景。',M,y,size=11)-23
    y = section(c,'先測模型，再連上動作',y)
    y = text(c,'另留每類至少 5 張新圖片測試。停止卡是分類教材，模型識別不取代工具停止按鈕或老師的現場停止方式。',M,y,size=11)
    finish(c,y,'printable cards')
    c.save()


if __name__ == '__main__':
    worksheets(); teacher_manual(); operations()
    print('Built 16-page worksheets, 18-page teacher manual and 5-page operations / field record / color cards.')
