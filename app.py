# -*- coding: utf-8 -*-
"""Campus Mate — 대화와 캡처로 일정·학업을 관리하는 AI 비서 (API 없이 동작하는 시연용 데모)

실행:  streamlit run app.py
"""
import base64
import calendar as pycal
import hashlib
import html
import json
import random
import re
import uuid
from datetime import date, datetime, timedelta, timezone

import requests
import streamlit as st

st.set_page_config(page_title="Campus Mate", page_icon="📎", layout="wide",
                   initial_sidebar_state="expanded")

# ─────────────────────────────────────────────────────────────
# 기본 상수
# ─────────────────────────────────────────────────────────────
TZ = timezone(timedelta(hours=9))
DAYS = ["월", "화", "수", "목", "금", "토", "일"]
ONLINE = "온라인"
CATS = ["과제", "시험", "팀플", "수업", "학사", "기타"]
CAT_COLOR = {"과제": "#F0567A", "시험": "#7C5CF0", "팀플": "#12A883",
             "수업": "#3D5AFE", "학사": "#8A93A8", "기타": "#E89A1C"}
STATUS = ["시작 전", "진행 중", "완료"]
STAGES = {3: ("3일 전", "과제 시작 알림", "이제 시작하면 여유 있게 끝낼 수 있어요."),
          2: ("2일 전", "진행 상황 확인", "어디까지 했는지 확인해 볼까요?"),
          1: ("1일 전", "최종 검토·제출 준비", "마지막으로 검토하고 제출 준비를 해요."),
          0: ("당일", "제출 여부 확인", "오늘이 마감이에요. 제출했나요?")}
LANGS = {"한국어": "ko", "English": "en", "日本語": "ja", "中文": "zh"}
SCHOOLS = ["세종대학교", "건국대학교", "한양대학교", "경희대학교", "서울시립대학교"]
BLOCK_COLORS = [("#E4E9FF", "#2A3FB8"), ("#FFE3EA", "#B4284C"), ("#DDF5EC", "#0B7257"),
                ("#FFF1C9", "#8A5A00"), ("#ECE5FF", "#5234B8"), ("#DFF1FB", "#125E86")]

SAMPLE_TIMETABLE = [
    {"강의명": "유통경로관리", "요일": "월", "시작": "10:30", "종료": "12:00", "강의실": "경영관 304"},
    {"강의명": "유통경로관리", "요일": "수", "시작": "10:30", "종료": "12:00", "강의실": "경영관 304"},
    {"강의명": "소비자행동론", "요일": "화", "시작": "13:30", "종료": "15:00", "강의실": "경영관 201"},
    {"강의명": "소비자행동론", "요일": "목", "시작": "13:30", "종료": "15:00", "강의실": "경영관 201"},
    {"강의명": "마케팅조사론", "요일": "월", "시작": "15:00", "종료": "16:30", "강의실": "경영관 412"},
    {"강의명": "마케팅조사론", "요일": "수", "시작": "15:00", "종료": "16:30", "강의실": "경영관 412"},
    {"강의명": "경영통계", "요일": "화", "시작": "09:00", "종료": "10:30", "강의실": "인문관 105"},
    {"강의명": "경영통계", "요일": "목", "시작": "09:00", "종료": "10:30", "강의실": "인문관 105"},
    {"강의명": "비즈니스영어", "요일": "금", "시작": "10:30", "종료": "12:00", "강의실": "어학관 203"},
]

# 전공 용어집: 과목 → [용어(ko/en/ja/zh), 해설(ko/en/ja/zh)]
GLOSSARY = {
    "유통경로관리": [
        {"t": {"ko": "유통경로", "en": "Distribution channel", "ja": "流通チャネル", "zh": "分销渠道"},
         "d": {"ko": "제품이 생산자에서 최종 소비자에게 전달되기까지 거치는 조직들의 연결망.",
               "en": "The network of organizations a product passes through from producer to final consumer.",
               "ja": "製品が生産者から最終消費者に届くまでに経由する組織のつながり。",
               "zh": "产品从生产者到最终消费者所经过的一系列组织。"}},
        {"t": {"ko": "경로 갈등", "en": "Channel conflict", "ja": "チャネル・コンフリクト", "zh": "渠道冲突"},
         "d": {"ko": "경로 구성원끼리 목표나 역할이 어긋나 생기는 마찰. 예: 본사 온라인몰과 대리점의 가격 충돌.",
               "en": "Friction between channel members whose goals or roles clash, e.g. a brand's online store undercutting its dealers.",
               "ja": "チャネル構成員の間で目標や役割が食い違って生じる摩擦。例：本社ECと代理店の価格衝突。",
               "zh": "渠道成员之间因目标或角色不一致而产生的摩擦，例如总部网店与经销商的价格冲突。"}},
        {"t": {"ko": "수직적 마케팅 시스템", "en": "Vertical marketing system (VMS)", "ja": "垂直的マーケティング・システム", "zh": "垂直营销系统"},
         "d": {"ko": "생산자·도매상·소매상이 하나의 체계처럼 통합되어 움직이는 경로 구조.",
               "en": "A channel structure in which producer, wholesaler and retailer act as one unified system.",
               "ja": "生産者・卸売業者・小売業者が一つの体系として統合されて動くチャネル構造。",
               "zh": "生产商、批发商和零售商作为一个统一体系运作的渠道结构。"}},
        {"t": {"ko": "옴니채널", "en": "Omnichannel", "ja": "オムニチャネル", "zh": "全渠道"},
         "d": {"ko": "온·오프라인 채널을 하나로 연결해 고객이 어디서든 같은 경험을 하게 하는 전략.",
               "en": "A strategy that connects online and offline channels so customers get one consistent experience.",
               "ja": "オンラインとオフラインのチャネルをつなぎ、どこでも同じ体験を提供する戦略。",
               "zh": "把线上线下渠道连成一体，让顾客在任何地方都获得一致体验的策略。"}},
    ],
    "소비자행동론": [
        {"t": {"ko": "관여도", "en": "Involvement", "ja": "関与", "zh": "涉入度"},
         "d": {"ko": "소비자가 제품이나 구매 결정에 대해 느끼는 개인적 중요성과 관심의 정도.",
               "en": "How personally important and interesting a product or purchase decision feels to a consumer.",
               "ja": "消費者が製品や購買決定に対して感じる個人的な重要性や関心の度合い。",
               "zh": "消费者对产品或购买决策所感受到的个人重要性和关心程度。"}},
        {"t": {"ko": "인지 부조화", "en": "Cognitive dissonance", "ja": "認知的不協和", "zh": "认知失调"},
         "d": {"ko": "구매 후 자신의 선택이 옳았는지 불안해하는 심리적 불편함.",
               "en": "The psychological discomfort of doubting whether a purchase was the right choice.",
               "ja": "購入後に自分の選択が正しかったか不安になる心理的な不快感。",
               "zh": "购买后怀疑自己的选择是否正确而产生的心理不适。"}},
        {"t": {"ko": "준거집단", "en": "Reference group", "ja": "準拠集団", "zh": "参照群体"},
         "d": {"ko": "개인의 태도와 구매 행동에 기준이 되는 집단.",
               "en": "A group that serves as a standard for a person's attitudes and buying behavior.",
               "ja": "個人の態度や購買行動の基準となる集団。",
               "zh": "作为个人态度和购买行为参照标准的群体。"}},
        {"t": {"ko": "고려상표군", "en": "Consideration set", "ja": "考慮集合", "zh": "考虑集"},
         "d": {"ko": "구매를 결정할 때 실제로 비교 대상에 올리는 브랜드 묶음.",
               "en": "The set of brands a consumer actually compares when deciding what to buy.",
               "ja": "購入を決めるときに実際に比較対象とするブランドの集まり。",
               "zh": "消费者做购买决定时真正拿来比较的品牌集合。"}},
    ],
    "마케팅조사론": [
        {"t": {"ko": "표본추출", "en": "Sampling", "ja": "標本抽出", "zh": "抽样"},
         "d": {"ko": "모집단 전체 대신 일부를 뽑아 조사하는 절차.",
               "en": "Selecting a part of the population to study instead of the whole.",
               "ja": "母集団全体の代わりに一部を選んで調査する手続き。",
               "zh": "从总体中抽取一部分进行调查的程序。"}},
        {"t": {"ko": "타당도", "en": "Validity", "ja": "妥当性", "zh": "效度"},
         "d": {"ko": "측정 도구가 측정하려는 개념을 실제로 측정하는 정도.",
               "en": "The extent to which a measure actually captures the concept it is meant to measure.",
               "ja": "測定用具が測ろうとする概念を実際に測定している程度。",
               "zh": "测量工具真正测到所要测量概念的程度。"}},
        {"t": {"ko": "신뢰도", "en": "Reliability", "ja": "信頼性", "zh": "信度"},
         "d": {"ko": "같은 대상을 반복 측정했을 때 결과가 일관되게 나오는 정도.",
               "en": "How consistent the results are when the same thing is measured repeatedly.",
               "ja": "同じ対象を繰り返し測定したときに結果が一貫している程度。",
               "zh": "对同一对象重复测量时结果保持一致的程度。"}},
        {"t": {"ko": "리커트 척도", "en": "Likert scale", "ja": "リッカート尺度", "zh": "李克特量表"},
         "d": {"ko": "동의하는 정도를 5점·7점 같은 단계로 답하게 하는 척도.",
               "en": "A scale that asks respondents to rate agreement in steps, such as 5 or 7 points.",
               "ja": "同意の度合いを5段階・7段階などで答えてもらう尺度。",
               "zh": "让受访者用5级或7级等来表示同意程度的量表。"}},
    ],
    "경영통계": [
        {"t": {"ko": "귀무가설", "en": "Null hypothesis", "ja": "帰無仮説", "zh": "原假设"},
         "d": {"ko": "차이나 효과가 없다고 가정하는 가설. 검정을 통해 기각 여부를 판단한다.",
               "en": "The hypothesis that there is no difference or effect; a test decides whether to reject it.",
               "ja": "差や効果がないと仮定する仮説。検定によって棄却するかどうかを判断する。",
               "zh": "假定没有差异或效果的假设，通过检验判断是否拒绝。"}},
        {"t": {"ko": "유의확률", "en": "p-value", "ja": "p値", "zh": "p值"},
         "d": {"ko": "귀무가설이 참일 때, 관측된 결과만큼 또는 그보다 극단적인 값이 나올 확률.",
               "en": "The probability of a result at least as extreme as the one observed, if the null hypothesis is true.",
               "ja": "帰無仮説が正しいとき、観測結果と同じかそれ以上に極端な値が出る確率。",
               "zh": "在原假设为真时，得到与观测结果同样或更极端结果的概率。"}},
        {"t": {"ko": "표준편차", "en": "Standard deviation", "ja": "標準偏差", "zh": "标准差"},
         "d": {"ko": "데이터가 평균에서 얼마나 흩어져 있는지를 나타내는 값.",
               "en": "A measure of how spread out the data are around the mean.",
               "ja": "データが平均からどれだけ散らばっているかを示す値。",
               "zh": "表示数据相对于平均值离散程度的数值。"}},
        {"t": {"ko": "회귀분석", "en": "Regression analysis", "ja": "回帰分析", "zh": "回归分析"},
         "d": {"ko": "한 변수가 다른 변수에 미치는 영향을 식으로 추정하는 분석 방법.",
               "en": "A method that estimates, as an equation, how one variable affects another.",
               "ja": "ある変数が別の変数に与える影響を式として推定する分析手法。",
               "zh": "用方程估计一个变量对另一个变量影响的分析方法。"}},
    ],
}

IDEAS = {
    "유통경로관리": ["본사 온라인몰과 대리점 사이의 가격 갈등 사례와 해결 방식 비교",
                 "편의점 퀵커머스가 기존 유통경로에 준 변화",
                 "D2C 브랜드가 오프라인 매장을 여는 이유",
                 "프랜차이즈 본부와 가맹점의 힘의 균형 분석"],
    "소비자행동론": ["내가 최근에 한 고관여 구매의 의사결정 과정 기록",
                 "숏폼 리뷰가 고려상표군에 미치는 영향",
                 "구매 후 인지 부조화를 줄이려는 브랜드의 장치들",
                 "대학생 준거집단과 패션 소비"],
    "마케팅조사론": ["학식 만족도 설문 설계: 척도와 문항 순서",
                 "편의표본과 확률표본의 결과 차이 실험",
                 "설문 문항의 타당도·신뢰도 점검 방법",
                 "에브리타임 게시글을 활용한 탐색 조사"],
    "경영통계": ["카페 대기시간 데이터로 가설검정 해 보기",
              "공부 시간과 성적의 회귀분석",
              "표본 크기가 p값에 주는 영향 시뮬레이션",
              "평균과 중앙값이 다르게 말하는 사례 찾기"],
}
GENERIC_IDEAS = ["수업에서 다룬 개념 하나를 골라 실제 사례에 적용하기",
                 "서로 반대되는 두 사례를 비교해 기준 세우기",
                 "내 경험에서 출발해 이론으로 설명하기",
                 "최근 1년 안의 기사에서 주제 찾기"]

PLAN_STEPS = {
    "과제": ["요구사항과 평가 기준 확인하기", "자료 조사하고 참고문헌 모으기", "개요 짜기",
           "초안 쓰기", "검토하기: 맞춤법, 분량, 출처", "제출하고 제출 완료 화면 저장하기"],
    "시험": ["시험 범위와 유형 확인하기", "강의자료 1회독하며 용어 정리하기", "요약 노트 만들기",
           "예상 문제 풀기", "틀린 부분 다시 보기", "전날 가볍게 훑고 일찍 자기"],
}

# ─────────────────────────────────────────────────────────────
# 스타일
# ─────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css');
:root{--ink:#1A2238;--sub:#5F6880;--mute:#98A0B4;--line:#E4E7F0;--paper:#F5F6FA;--card:#FFFFFF;
--blue:#3D5AFE;--blue-soft:#EEF1FF;--mark:#FFE45C;}
html,body,.stApp,.stMarkdown,p,h1,h2,h3,h4,h5,label,button,input,textarea,select,li,td,th{
font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;}
.stApp{background:var(--paper);color:var(--ink);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stMain"] .block-container{max-width:1240px;padding:2.2rem 2.4rem 5rem;}
[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line);}
[data-testid="stSidebar"] .stButton>button{justify-content:flex-start;border:0;border-radius:10px;padding:.55rem .8rem;font-weight:600;color:var(--sub);background:transparent;}
[data-testid="stSidebar"] .stButton>button>div{justify-content:flex-start;width:100%;}
[data-testid="stSidebar"] .stButton>button:hover{background:var(--paper);color:var(--ink);}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:var(--ink);color:#fff;}
[data-testid="stSidebar"] .stButton>button[kind="primary"]:hover{background:var(--ink);color:#fff;}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"]>button{border-radius:10px;font-weight:650;}
.stButton>button:focus-visible{outline:2px solid var(--blue);outline-offset:2px;}
[data-testid="stMain"] .stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primary"]{background:var(--blue);border-color:var(--blue);color:#fff;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px;}
div[data-testid="stChatMessage"]{background:transparent;padding:.35rem 0;gap:.7rem;}
div[data-testid="stChatInput"]>div{border-radius:16px;border:1.5px solid var(--line);box-shadow:0 10px 30px rgba(26,34,56,.08);}

.cm-brand{display:flex;align-items:center;gap:10px;padding:4px 4px 18px;}
.cm-logo{width:38px;height:38px;border-radius:11px;background:var(--ink);display:flex;align-items:center;justify-content:center;position:relative;}
.cm-logo:before{content:"";width:16px;height:16px;border:3px solid #fff;border-radius:50%;}
.cm-logo:after{content:"";position:absolute;right:7px;bottom:7px;width:9px;height:9px;border-radius:50%;background:var(--mark);}
.cm-brand b{font-size:17px;font-weight:800;letter-spacing:-.03em;color:var(--ink);display:block;line-height:1.2;}
.cm-brand span{font-size:12px;color:var(--mute);}
.cm-me{margin-top:14px;padding:12px;border-radius:12px;background:var(--paper);font-size:12.5px;color:var(--sub);line-height:1.6;}
.cm-me b{color:var(--ink);font-size:14px;}

.cm-h1{font-size:34px;font-weight:800;letter-spacing:-.045em;line-height:1.25;color:var(--ink);margin:0 0 6px;}
.cm-h1 mark,.cm-mark{background:linear-gradient(transparent 58%,var(--mark) 58%,var(--mark) 92%,transparent 92%);color:inherit;padding:0 2px;}
.cm-lead{font-size:15px;color:var(--sub);line-height:1.65;margin:0 0 22px;max-width:62ch;}
.cm-h2{font-size:17px;font-weight:750;letter-spacing:-.02em;color:var(--ink);margin:6px 0 10px;}
.cm-note{font-size:12.5px;color:var(--mute);line-height:1.6;}
.cm-demo{display:inline-block;font-size:11.5px;font-weight:650;color:#7A5A00;background:#FFF6CC;border-radius:6px;padding:2px 7px;}

.cm-chip{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:700;border-radius:999px;padding:2px 9px;line-height:1.6;}
.cm-dday{font-size:11.5px;font-weight:800;border-radius:6px;padding:2px 7px;background:var(--ink);color:#fff;}
.cm-dday.hot{background:#F0567A;}
.cm-dday.done{background:#DDE1EC;color:#6B7389;}

.cm-row{display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--line);}
.cm-row:last-child{border-bottom:0;}
.cm-row .t{width:46px;flex:none;font-size:12.5px;font-weight:700;color:var(--sub);padding-top:1px;font-variant-numeric:tabular-nums;}
.cm-row .bar{width:4px;align-self:stretch;border-radius:4px;flex:none;}
.cm-row .b{font-size:14px;font-weight:650;color:var(--ink);line-height:1.4;}
.cm-row .s{font-size:12px;color:var(--mute);margin-top:2px;}
.cm-empty{font-size:13px;color:var(--mute);padding:14px 0;}

.cm-alert{border-radius:14px;padding:12px 14px;background:#fff;border:1px solid var(--line);margin-bottom:8px;border-left:5px solid var(--mark);}
.cm-alert .k{font-size:11.5px;font-weight:800;color:#8A6A00;}
.cm-alert .b{font-size:14px;font-weight:700;color:var(--ink);margin:2px 0;}
.cm-alert .s{font-size:12.5px;color:var(--sub);}

.cm-cand{border-radius:14px;background:#fff;border:1.5px solid var(--ink);padding:14px 16px;margin:6px 0 4px;}
.cm-cand .b{font-size:16px;font-weight:800;letter-spacing:-.02em;margin:6px 0 8px;}
.cm-cand dl{display:grid;grid-template-columns:64px 1fr;gap:4px 10px;margin:0;font-size:13px;}
.cm-cand dt{color:var(--mute);font-weight:600;}
.cm-cand dd{margin:0;color:var(--ink);font-weight:600;}
.cm-ok{font-size:13px;font-weight:700;color:#0B7257;}

.cm-shot{border-radius:12px;background:#fff;border:1px solid var(--line);padding:14px 16px;max-width:420px;font-size:13px;line-height:1.7;color:var(--ink);box-shadow:0 6px 18px rgba(26,34,56,.07);}
.cm-shot .bar{font-size:11px;color:var(--mute);border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:8px;display:flex;justify-content:space-between;}
.cm-shot b{font-size:14px;}

.cm-cal{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border:1px solid var(--line);border-radius:16px;overflow:hidden;background:#fff;}
.cm-cal .hd{font-size:12px;font-weight:700;color:var(--mute);padding:10px 10px 8px;border-bottom:1px solid var(--line);}
.cm-cal .c{min-height:104px;padding:8px 8px 10px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);overflow:hidden;}
.cm-cal .c:nth-child(7n){border-right:0;}
.cm-cal .c.out{background:#FAFBFD;}
.cm-cal .c.out .n{color:#C5CAD8;}
.cm-cal .n{font-size:13px;font-weight:700;color:var(--sub);display:inline-flex;width:24px;height:24px;align-items:center;justify-content:center;border-radius:50%;margin-bottom:4px;}
.cm-cal .c.today .n{background:var(--ink);color:#fff;}
.cm-cal .e{display:block;font-size:11.5px;font-weight:650;border-radius:5px;padding:2px 6px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.cm-cal .more{font-size:11px;color:var(--mute);margin-top:3px;padding-left:4px;}

.cm-tt{display:grid;grid-template-columns:44px repeat(5,minmax(0,1fr));background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden;}
.cm-tt .hd{font-size:12.5px;font-weight:700;color:var(--sub);text-align:center;padding:10px 0;border-bottom:1px solid var(--line);}
.cm-tt .hd.on{color:var(--ink);background:linear-gradient(transparent 62%,var(--mark) 62%,var(--mark) 86%,transparent 86%);}
.cm-tt .hours div{height:60px;font-size:11px;color:var(--mute);text-align:right;padding:4px 8px 0 0;font-variant-numeric:tabular-nums;}
.cm-tt .col{position:relative;border-left:1px solid var(--line);background-image:linear-gradient(var(--line) 1px,transparent 1px);background-size:100% 60px;}
.cm-tt .blk{position:absolute;left:4px;right:4px;border-radius:9px;padding:7px 9px;overflow:hidden;}
.cm-tt .blk b{display:block;font-size:12.5px;font-weight:750;line-height:1.3;}
.cm-tt .blk span{font-size:11px;opacity:.85;}

.cm-task{background:#fff;border:1px solid var(--line);border-radius:14px;padding:13px 14px 12px;margin-bottom:4px;}
.cm-task .top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}
.cm-task .b{font-size:14.5px;font-weight:750;letter-spacing:-.01em;line-height:1.4;}
.cm-task .s{font-size:12px;color:var(--mute);margin-top:3px;}
.cm-track{display:flex;gap:4px;margin-top:10px;}
.cm-track i{flex:1;height:5px;border-radius:5px;background:#E9ECF4;}
.cm-track i.on{background:var(--mark);}
.cm-track i.now{background:#F0567A;}
.cm-colhd{font-size:13px;font-weight:750;color:var(--sub);margin:0 0 10px;display:flex;gap:6px;align-items:center;}
.cm-colhd em{font-style:normal;font-size:12px;color:var(--mute);font-weight:600;}

.cm-term{background:#fff;border:1px solid var(--line);border-radius:14px;padding:13px 16px;margin-bottom:8px;}
.cm-term .b{font-size:15px;font-weight:800;}
.cm-term .o{font-size:13px;color:var(--blue);font-weight:650;margin-left:8px;}
.cm-term p{font-size:13.5px;color:var(--sub);line-height:1.65;margin:5px 0 0;}
.cm-steps{counter-reset:s;display:flex;gap:6px;margin:0 0 22px;padding:0;list-style:none;}
.cm-steps li{counter-increment:s;flex:1;font-size:13px;font-weight:650;color:var(--mute);border-top:4px solid #E1E5EF;padding-top:8px;}
.cm-steps li:before{content:counter(s) ". ";}
.cm-steps li.on{color:var(--ink);border-color:var(--ink);}
.cm-steps li.done{color:var(--sub);border-color:var(--mark);}
@media (max-width:760px){[data-testid="stMain"] .block-container{padding:1.2rem 1rem 5rem;}.cm-h1{font-size:26px;}.cm-cal .c{min-height:72px;padding:5px;}.cm-cal .e{font-size:10px;padding:1px 4px;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────
def H(markup):
    st.markdown(markup, unsafe_allow_html=True)


def esc(v):
    return html.escape(str(v if v is not None else ""))


def uid():
    return uuid.uuid4().hex[:12]


def now():
    return datetime.now(TZ)


def today():
    return now().date()


def dparse(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def fmt_date(d):
    if not d:
        return "날짜 미정"
    return f"{d.month}월 {d.day}일({DAYS[d.weekday()]})"


def dday(d):
    n = (d - today()).days
    return "D-DAY" if n == 0 else (f"D-{n}" if n > 0 else f"D+{-n}")


def chip(cat):
    c = CAT_COLOR.get(cat, "#8A93A8")
    return f'<span class="cm-chip" style="background:{c}1A;color:{c}">{esc(cat)}</span>'


def lang_key():
    return LANGS.get(st.session_state.profile.get("lang", "한국어"), "ko")


def courses():
    seen = []
    for e in st.session_state.events:
        if e["category"] == "수업" and e["course"] and e["course"] not in seen:
            seen.append(e["course"])
    return seen


def go(page, **kw):
    st.session_state.page = page
    for k, v in kw.items():
        st.session_state[k] = v


def new_event(title, category, d, time="", end_time="", course="", weekly=False, until=None,
              end=None, location="", details="", status="시작 전", source="직접 입력"):
    return {"id": uid(), "title": title, "category": category,
            "date": d.isoformat() if d else "", "end": end.isoformat() if end else "",
            "time": time, "end_time": end_time, "course": course, "weekly": weekly,
            "until": until.isoformat() if until else "", "location": location,
            "details": details, "status": status, "source": source}


def get_event(eid):
    for e in st.session_state.events:
        if e["id"] == eid:
            return e
    return None


def events_on(day, include_classes=True):
    out = []
    for e in st.session_state.events:
        d0 = dparse(e["date"])
        if not d0:
            continue
        if e["weekly"]:
            if not include_classes and e["category"] == "수업":
                continue
            until = dparse(e["until"])
            if day >= d0 and (day - d0).days % 7 == 0 and (not until or day <= until):
                out.append(e)
        else:
            d1 = dparse(e["end"]) or d0
            if d0 <= day <= d1:
                out.append(e)
    out.sort(key=lambda x: x["time"] or "99:99")
    return out


def todo_items():
    """마감이 있는 할 일(과제·시험)."""
    items = [e for e in st.session_state.events
             if e["category"] in ("과제", "시험") and not e["weekly"] and dparse(e["date"])]
    items.sort(key=lambda x: (x["date"], x["time"] or "99:99"))
    return items


def alerts():
    out = []
    on = st.session_state.stages
    for e in todo_items():
        if e["status"] == "완료":
            continue
        n = (dparse(e["date"]) - today()).days
        if n < 0:
            out.append((e, "마감 지남", "마감이 지났어요", "제출했다면 완료로 바꿔 주세요."))
        elif n in STAGES and on.get(n, True):
            k, t, s = STAGES[n]
            out.append((e, k, t, s))
    return out


# ─────────────────────────────────────────────────────────────
# 예시 데이터 (데모용)
# ─────────────────────────────────────────────────────────────
def semester_frame():
    """오늘을 기준으로 한 예시 학기. 기말 주간의 월요일(fm)을 기준점으로 잡는다."""
    t = today()
    probe = t + timedelta(days=18)
    fm = probe - timedelta(days=probe.weekday())
    start = (t - timedelta(days=t.weekday())) - timedelta(weeks=11)
    return start, fm


def academic_events(school):
    _, fm = semester_frame()
    src = f"{school} 학사일정(예시)"
    return [
        new_event("강의평가 기간", "학사", fm - timedelta(days=7), end=fm + timedelta(days=4), source=src),
        new_event("기말고사 기간", "학사", fm, end=fm + timedelta(days=4), source=src),
        new_event("종강", "학사", fm + timedelta(days=4), source=src),
        new_event("성적 열람 시작", "학사", fm + timedelta(days=9), source=src),
        new_event("다음 학기 수강신청", "학사", fm + timedelta(days=28), end=fm + timedelta(days=30), source=src),
    ]


def class_events(rows):
    start, fm = semester_frame()
    until = fm - timedelta(days=3)
    out = []
    for r in rows:
        name = str(r.get("강의명") or "").strip()
        day = str(r.get("요일") or "").strip()
        if not name:
            continue
        if day not in DAYS:
            out.append(new_event(name, "수업", None, course=name, location=ONLINE, source="시간표 캡처"))
            continue
        first = start + timedelta(days=DAYS.index(day))
        out.append(new_event(name, "수업", first, time=str(r.get("시작") or "").strip(),
                             end_time=str(r.get("종료") or "").strip(), course=name, weekly=True,
                             until=until, location=str(r.get("강의실") or "").strip(),
                             source="시간표 캡처"))
    return out


def sample_tasks():
    t = today()
    return [
        new_event("팀 프로젝트 중간보고서", "과제", t + timedelta(days=3), time="23:59", course="유통경로관리",
                  details="주제: 국내 기업의 유통경로 갈등 사례 분석\n제출: LMS 과제함에 PDF 업로드\n분량: A4 5매 이내",
                  source="공지 캡처"),
        new_event("설문지 초안 제출", "과제", t + timedelta(days=1), time="18:00", course="마케팅조사론",
                  details="리커트 척도 문항 10개 이상\n제출: 수업 시간에 출력본 제출", status="진행 중", source="대화"),
        new_event("3주차 범위 퀴즈", "시험", t + timedelta(days=6), time="09:00", course="경영통계",
                  details="범위: 가설검정, p값\n방식: 수업 시작 직후 20분", source="대화"),
        new_event("유통 팀플 회의", "팀플", t + timedelta(days=1), time="19:00", course="유통경로관리",
                  location="학생회관 스터디룸 2", details="역할 분담, 사례 기업 확정", source="대화"),
    ]


# ─────────────────────────────────────────────────────────────
# 이미지 인식 (Gemini · Secrets에 GEMINI_API_KEY가 있을 때만 동작)
# ─────────────────────────────────────────────────────────────
GEMINI_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]


def _secret(name):
    try:
        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def _bad_key(v):
    """헤더로 보낼 수 없는 값(한글, 빈칸, 줄바꿈)이 섞였는지 본다."""
    return (not v.isascii()) or bool(re.search(r"\s", v))


def _net_err(e):
    if isinstance(e, requests.exceptions.Timeout):
        return "AI 응답이 너무 오래 걸려서 멈췄어요. 한 번 더 시도해 주세요."
    return f"AI 서버에 연결하지 못했어요 ({type(e).__name__}). 잠시 뒤 다시 시도해 주세요."


def ai_ready():
    return bool(_secret("GEMINI_API_KEY"))


GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"


def _err_detail(r):
    try:
        return str(r.json().get("error", {}).get("message", ""))[:160]
    except Exception:
        return ""


def gemini_models(key):
    """이 키로 지금 쓸 수 있는 모델을 구글에 물어보고, 쓸 만한 순서로 돌려준다."""
    if st.session_state.get("gm_list"):
        return st.session_state.gm_list, ""
    try:
        r = requests.get(f"{GEMINI_API}/models", headers={"x-goog-api-key": key},
                         params={"pageSize": 1000}, timeout=30)
    except Exception as e:
        return [], _net_err(e)
    if r.status_code != 200:
        return [], f"모델 목록을 받지 못했어요 (코드 {r.status_code}). {_err_detail(r)}"
    scored = []
    for m in r.json().get("models", []):
        name = str(m.get("name", "")).split("/")[-1]
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if not name.startswith("gemini") or re.search(r"image|tts|live|audio|embed|native|robot|computer", name):
            continue
        v = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
        ver = float(v.group(1)) if v else 0.0
        score = ver
        score += 100 if "flash" in name else 0
        score -= 50 if "lite" in name else 0
        score -= 0.05 if re.search(r"preview|exp", name) else 0
        score += 0.01 if "latest" in name else 0
        scored.append((score, name))
    names = [n for _, n in sorted(scored, reverse=True)]
    if names:
        st.session_state.gm_list = names
    return names, "" if names else "이 키로 쓸 수 있는 Gemini 모델이 없어요."


def gemini_json(data, mime, prompt):
    """이미지(또는 PDF)와 지시문을 보내 JSON을 돌려받는다. (결과, 오류문구)"""
    key = _secret("GEMINI_API_KEY")
    if not key:
        return None, "API 키가 설정되지 않았어요."
    if _bad_key(key):
        return None, ("Secrets의 GEMINI_API_KEY 값에 한글이나 빈칸, 줄바꿈이 섞여 있어요. "
                      "AI Studio에서 키를 다시 복사해 따옴표 안에 붙여 넣어 주세요.")
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": mime or "image/png", "data": base64.b64encode(data).decode()}},
        {"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    custom = _secret("GEMINI_MODEL")
    found, list_err = gemini_models(key)
    order = []
    for m in ([custom] if custom else []) + found[:6] + GEMINI_MODELS:
        if m and m not in order:
            order.append(m)
    err = list_err or "응답을 받지 못했어요."
    for model in order:
        try:
            r = requests.post(f"{GEMINI_API}/models/{model}:generateContent",
                              headers={"x-goog-api-key": key}, json=body, timeout=90)
        except Exception as e:
            err = _net_err(e)
            continue
        if r.status_code == 200:
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts).strip()
                text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
                st.session_state.gm_list = [model] + [m for m in found if m != model]
                return json.loads(text), ""
            except Exception:
                err = "AI 응답을 해석하지 못했어요. 한 번 더 시도해 주세요."
                continue
        if r.status_code in (401, 403):
            return None, f"API 키에 문제가 있어요 (코드 {r.status_code}). Secrets의 키를 확인해 주세요. {_err_detail(r)}"
        if r.status_code == 429:
            err = "무료 사용 한도를 잠시 넘었어요. 1분쯤 뒤에 다시 시도해 주세요."
            continue
        if r.status_code == 404:
            err = list_err or f"모델 {model}을(를) 쓸 수 없어요. {_err_detail(r)}"
            continue
        err = f"AI 요청이 실패했어요 (모델 {model}, 코드 {r.status_code}). {_err_detail(r)}"
    return None, err


def _hhmm(v):
    m = re.match(r"^\s*(\d{1,2})[:시]\s*(\d{2})?", str(v or ""))
    if not m or int(m.group(1)) > 23:
        return ""
    return f"{int(m.group(1)):02d}:{m.group(2) or '00'}"


def read_timetable(data, mime):
    prompt = ("이 이미지는 한국 대학생의 주간 시간표(에브리타임 등) 캡처다. 모든 수업 칸을 읽어 JSON 배열로만 답하라. "
              "같은 수업이 여러 요일에 있으면 요일마다 항목을 따로 만든다. 각 항목의 키: "
              '"강의명"(문자열), "요일"("월","화","수","목","금","토","일" 중 하나), '
              '"시작"("HH:MM" 24시간제), "종료"("HH:MM"), "강의실"(없으면 빈 문자열). '
              "시간은 왼쪽 시간 눈금과 칸의 위치로 판단한다. "
              "격자 아래나 바깥에 따로 적힌 온라인 강의·시간 미지정 강의(예: K-MOOC, 사이버 강의)도 빠짐없이 포함하되, "
              '그런 항목은 "요일"을 "온라인"으로, "시작"과 "종료"를 빈 문자열로 둔다. '
              "시간표가 아니면 빈 배열 []을 답하라.")
    out, err = gemini_json(data, mime, prompt)
    if err:
        return None, err
    if isinstance(out, dict):
        out = next((v for v in out.values() if isinstance(v, list)), [])
    rows = []
    for r in out if isinstance(out, list) else []:
        if not isinstance(r, dict):
            continue
        name, day = str(r.get("강의명") or "").strip(), str(r.get("요일") or "").strip()[:1]
        if name and day in DAYS:
            rows.append({"강의명": name, "요일": day, "시작": _hhmm(r.get("시작")), "종료": _hhmm(r.get("종료")),
                         "강의실": str(r.get("강의실") or "").strip()})
        elif name:
            rows.append({"강의명": name, "요일": ONLINE, "시작": "", "종료": "",
                         "강의실": str(r.get("강의실") or "").strip()})
    if not rows:
        return None, "사진에서 수업을 찾지 못했어요. 시간표 전체가 보이는 캡처인지 확인해 주세요."
    rows.sort(key=lambda r: (DAYS.index(r["요일"]) if r["요일"] in DAYS else 9, r["시작"]))
    return rows, ""


def read_notice(data, mime):
    t = today()
    prompt = (f"오늘은 {t.isoformat()}({DAYS[t.weekday()]}요일)이다. 이 자료는 대학 수업 공지, 과제 안내, 단톡방 캡처 중 하나다. "
              "여기서 학생이 캘린더에 등록해야 할 가장 중요한 일정 하나를 찾아 JSON 객체로만 답하라. 키: "
              '"found"(일정이 있으면 true), "title"(20자 이내 일정 이름), '
              f'"course"(과목명. 다음 중 해당하면 그대로 사용: {", ".join(courses()) or "없음"}. 모르면 빈 문자열), '
              '"category"("과제","시험","팀플","수업","학사","기타" 중 하나), "date"("YYYY-MM-DD", 마감일 또는 일정 날짜), '
              '"time"("HH:MM" 24시간제, 없으면 빈 문자열), "location"(없으면 빈 문자열), '
              '"how"(제출 방식, 없으면 빈 문자열), "size"(분량, 없으면 빈 문자열), "topic"(주제나 범위, 없으면 빈 문자열). '
              "연도가 없으면 오늘 이후의 가장 가까운 날짜로 해석한다.")
    out, err = gemini_json(data, mime, prompt)
    if err:
        return None, err
    if isinstance(out, list) and out:
        out = out[0]
    if not isinstance(out, dict) or not out.get("found", True) or not dparse(out.get("date")):
        return None, "자료에서 날짜가 있는 일정을 찾지 못했어요. 일정을 말로 알려 주시면 등록할게요."
    cat = out.get("category") if out.get("category") in CATS else "기타"
    det = [f"{k}: {str(out.get(f) or '').strip()}" for k, f in (("주제", "topic"), ("제출", "how"), ("분량", "size"))
           if str(out.get(f) or "").strip()]
    course = str(out.get("course") or "").strip()
    return {"id": uid(), "title": str(out.get("title") or "새 일정").strip()[:40], "category": cat,
            "course": course, "date": dparse(out["date"]).isoformat(), "time": _hhmm(out.get("time")),
            "location": str(out.get("location") or "").strip(), "details": "\n".join(det),
            "source": "공지 캡처", "state": "확인 필요"}, ""


# ─────────────────────────────────────────────────────────────
# 대화 이해 (규칙 기반 · API 없음)
# ─────────────────────────────────────────────────────────────
KW = [("시험", ["중간고사", "기말고사", "퀴즈", "쪽지시험", "시험", "테스트"]),
      ("팀플", ["팀플 회의", "조모임", "팀플", "팀 회의", "회의", "미팅"]),
      ("과제", ["중간보고서", "보고서", "레포트", "리포트", "에세이", "발표자료", "발표", "과제", "제출", "숙제"]),
      ("수업", ["보강", "휴강", "수업", "강의"]),
      ("학사", ["수강신청", "등록금", "장학금", "휴학"])]


def _safe_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_date(text):
    t = today()
    hits = []
    m = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일?", text)
    if m:
        d = _safe_date(t.year, int(m.group(1)), int(m.group(2)))
        if d and d < t - timedelta(days=60):
            d = _safe_date(t.year + 1, d.month, d.day)
        if d:
            return d, [m.group(0)]
    m = re.search(r"(?<![\d:])(\d{1,2})[/.](\d{1,2})(?![\d:])", text)
    if m:
        d = _safe_date(t.year, int(m.group(1)), int(m.group(2)))
        if d and d < t - timedelta(days=60):
            d = _safe_date(t.year + 1, d.month, d.day)
        if d:
            return d, [m.group(0)]
    for word, off in (("오늘", 0), ("내일모레", 2), ("내일", 1), ("모레", 2), ("글피", 3)):
        if word in text:
            return t + timedelta(days=off), [word]
    m = re.search(r"(이번|다음|다다음)\s*주\s*([월화수목금토일])요일", text)
    if m:
        wk = {"이번": 0, "다음": 1, "다다음": 2}[m.group(1)]
        mon = t - timedelta(days=t.weekday())
        return mon + timedelta(weeks=wk, days=DAYS.index(m.group(2))), [m.group(0)]
    m = re.search(r"(이번|다음)\s*주", text)
    wk_only = m
    m = re.search(r"([월화수목금토일])요일", text)
    if m:
        diff = (DAYS.index(m.group(1)) - t.weekday()) % 7
        return t + timedelta(days=diff), [m.group(0)]
    m = re.search(r"(\d{1,2})\s*일\s*(뒤|후)", text)
    if m:
        return t + timedelta(days=int(m.group(1))), [m.group(0)]
    m = re.search(r"(일주일|1주일|한\s*주)\s*(뒤|후)", text)
    if m:
        return t + timedelta(days=7), [m.group(0)]
    m = re.search(r"(?<!\d)(\d{1,2})일(?!\s*(뒤|후|전|차))", text)
    if m:
        d = _safe_date(t.year, t.month, int(m.group(1)))
        if d and d < t:
            y, mo = (t.year + 1, 1) if t.month == 12 else (t.year, t.month + 1)
            d = _safe_date(y, mo, int(m.group(1)))
        if d:
            return d, [m.group(0)]
    if wk_only:
        mon = t - timedelta(days=t.weekday())
        return mon + timedelta(weeks=1 if wk_only.group(1) == "다음" else 0, days=4), [wk_only.group(0)]
    return None, hits


def parse_time(text):
    m = re.search(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", text)
    if m and int(m.group(1)) < 24 and int(m.group(2)) < 60:
        return f"{int(m.group(1)):02d}:{m.group(2)}", [m.group(0)]
    if "자정" in text:
        return "23:59", ["자정"]
    if "정오" in text:
        return "12:00", ["정오"]
    m = re.search(r"(오전|오후|아침|낮|저녁|밤|새벽)?\s*(\d{1,2})\s*시\s*(반|\d{1,2}\s*분)?", text)
    if m:
        ap, h = m.group(1), int(m.group(2))
        mi = 0
        if m.group(3):
            mi = 30 if m.group(3) == "반" else int(re.sub(r"\D", "", m.group(3)))
        if h > 24 or mi > 59:
            return "", []
        if ap in ("오후", "낮", "저녁", "밤") and h < 12:
            h += 12
        elif ap is None and 1 <= h <= 7:
            h += 12
        if h == 24 or (ap == "밤" and h == 12):
            h, mi = 23, 59
        return f"{h:02d}:{mi:02d}", [m.group(0)]
    return "", []


def find_course(text):
    compact = text.replace(" ", "").lower()
    names = []
    for c in courses():
        whole = c.replace(" ", "").lower()
        parts = [x for x in whole.split(":") if len(x) >= 2]
        names.append((c, [whole] + parts[::-1]))
    for c, al in names:
        for x in al:
            if x in compact:
                return c, x
    for n in (4, 3, 2):
        for c, al in names:
            for x in al:
                if len(x) > n and x[:n] in compact:
                    return c, x[:n]
    return "", ""


def find_kw(text):
    for cat, words in KW:
        for w in words:
            if w in text:
                return cat, w
    return "", ""


def understand(text):
    """문장에서 일정 후보를 뽑는다. 날짜도 유형도 없으면 None."""
    d, dhit = parse_date(text)
    tm, thit = parse_time(text)
    cat, word = find_kw(text)
    course, chit = find_course(text)
    if not d and not cat:
        return None
    if not cat:
        cat = "기타"
    if cat == "과제" and not tm:
        tm = "23:59"
    rest = text
    for h in dhit + thit:
        rest = rest.replace(h, " ")
    rest = re.sub(r"(까지|있어요|있어|해야 해|해야 돼|해 줘|해줘|등록|추가)", " ", rest)
    rest = re.sub(r"[.,!?~]+", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    if word in ("제출", "과제", "숙제"):
        title = "과제 제출"
    elif word:
        title = word
    else:
        title = rest[:28] or "새 일정"
    return {"id": uid(), "title": title, "category": cat, "course": course,
            "date": d.isoformat() if d else "", "time": tm, "location": "",
            "details": "", "source": "대화", "state": "확인 필요"}


def find_dup(c):
    for e in st.session_state.events:
        if e["weekly"] or e["date"] != c["date"] or e["category"] != c["category"]:
            continue
        if (c["course"] and e["course"] == c["course"]) or e["title"] == c["title"]:
            return e
    return None


def pick_task(text):
    """문장에 맞는 미완료 할 일을 고른다. 없으면 가장 급한 것."""
    todo = [e for e in todo_items() if e["status"] != "완료"]
    if not todo:
        return None
    course, _ = find_course(text)
    for e in todo:
        if (course and e["course"] == course) or e["title"] in text:
            return e
    return todo[0]


def lookup_term(text):
    low = text.lower().replace(" ", "")
    for course, terms in GLOSSARY.items():
        for g in terms:
            for v in g["t"].values():
                key = v.lower().replace(" ", "")
                key = re.sub(r"\(.*?\)", "", key)
                if key and key in low:
                    return course, g
    return None, None


def say(role, content, **extra):
    st.session_state.messages.append({"id": uid(), "role": role, "content": content, **extra})


def notice_sample():
    d = today() + timedelta(days=7)
    return {"course": "소비자행동론", "title": "개인 과제: 구매 의사결정 일지",
            "date": d, "time": "23:59", "how": "LMS 과제함에 PDF 업로드", "size": "A4 3매 이내"}


def respond_to_capture(upload=None):
    if upload is not None and ai_ready():
        with st.spinner("자료를 읽고 있어요"):
            cand, err = read_notice(upload.getvalue(), getattr(upload, "type", "") or "image/png")
        if err:
            say("assistant", err)
            return
        st.session_state.candidates[cand["id"]] = cand
        say("assistant", "올려 주신 자료에서 일정을 찾았어요. 맞는지 확인해 주세요.", cand=cand["id"])
        return
    n = notice_sample()
    cand = {"id": uid(), "title": n["title"], "category": "과제", "course": n["course"],
            "date": n["date"].isoformat(), "time": n["time"], "location": "",
            "details": f"제출: {n['how']}\n분량: {n['size']}", "source": "공지 캡처", "state": "확인 필요"}
    st.session_state.candidates[cand["id"]] = cand
    pre = ""
    if upload is not None:
        pre = ("AI 키가 연결되지 않아 올린 자료를 실제로 읽지는 못했어요. "
               "대신 예시 공지로 인식 과정을 보여 드릴게요.\n\n")
    say("assistant", pre + "공지에서 과목, 과제 내용, 마감일, 제출 방식을 찾았어요. 맞는지 확인해 주세요.",
        cand=cand["id"])


def respond(text):
    t = text.strip()
    # 1) 과제 시작
    if re.search(r"시작(할래|하자|할게|해\s*볼|하고\s*싶)", t) or "같이 공부" in t or "같이 하자" in t:
        e = pick_task(t)
        if e:
            if e["status"] == "시작 전":
                e["status"] = "진행 중"
            say("assistant", f"좋아요, **{e['course']} {e['title']}** 시작해 봐요. "
                f"마감은 {fmt_date(dparse(e['date']))} {e['time']}이에요. "
                "요구사항 정리부터 초안 피드백까지 같이 할 수 있어요.", study=e["id"])
        else:
            say("assistant", "아직 등록된 과제나 시험이 없어요. 먼저 일정을 알려 주세요. "
                "예: “금요일까지 유통 보고서 제출”")
        return
    # 2) 완료 보고
    if re.search(r"(제출했|다\s*했|끝냈|완료했|냈어)", t):
        e = pick_task(t)
        if e:
            e["status"] = "완료"
            say("assistant", f"수고했어요! **{e['title']}** 완료로 바꿨어요. 남은 알림도 꺼 둘게요.")
            return
    # 3) 오늘·내일 일정 묻기
    if re.search(r"(오늘|내일).*(뭐|일정|수업|알려)", t) and not find_kw(t.replace("일정", "").replace("수업", ""))[0]:
        day = today() + timedelta(days=1 if "내일" in t else 0)
        items = events_on(day)
        if items:
            lines = "\n".join(f"- {e['time'] or '종일'} {e['title']}" + (f" · {e['location']}" if e["location"] else "")
                              for e in items)
            say("assistant", f"{fmt_date(day)} 일정이에요.\n\n{lines}")
        else:
            say("assistant", f"{fmt_date(day)}에는 등록된 일정이 없어요.")
        return
    # 4) 용어 질문
    if re.search(r"(뜻|의미|뭐야|뭐예요|무슨|설명|번역|meaning|what is)", t, re.I):
        course, g = lookup_term(t)
        if g:
            k = lang_key()
            other = g["t"]["en"] if k == "ko" else g["t"][k]
            body = g["d"][k] if k != "ko" else g["d"]["ko"]
            extra = "" if k == "ko" else f"\n\n한국어 설명: {g['d']['ko']}"
            say("assistant", f"**{g['t']['ko']}** ({other})\n\n{body}{extra}\n\n{course} 수업에서 자주 나오는 용어예요.")
            return
    # 5) 일정 등록
    cand = understand(t)
    if cand:
        if not cand["date"]:
            say("assistant", "어떤 일정인지는 알겠어요. 날짜를 알려 주면 등록할게요. 예: “다음 주 수요일”, “12월 3일”")
            return
        st.session_state.candidates[cand["id"]] = cand
        say("assistant", "이렇게 이해했어요. 맞으면 캘린더에 등록할게요.", cand=cand["id"])
        return
    say("assistant", "일정이나 과제를 편하게 말해 주세요. 이런 식으로요.\n\n"
        "- “다음 주 수요일까지 유통 보고서 제출”\n- “12월 3일 오후 2시에 팀플 회의”\n"
        "- “이 과제 이제 시작할래”\n- “경로 갈등이 무슨 뜻이야?”")


def greeting():
    p = st.session_state.profile
    h = now().hour
    hello = "좋은 아침이에요" if h < 11 else ("좋은 오후예요" if h < 18 else "좋은 저녁이에요")
    t = today()
    cls = [e for e in events_on(t) if e["category"] == "수업"]
    parts = [f"{hello}, {p['name']}님!"]
    if cls:
        parts.append("오늘은 " + ", ".join(f"**{e['title']}**({e['time']})" for e in cls) + " 수업이 있어요.")
    else:
        parts.append("오늘은 수업이 없는 날이에요.")
    soon = [e for e in todo_items() if e["status"] != "완료" and 0 <= (dparse(e["date"]) - t).days <= 3]
    if soon:
        parts.append("마감이 가까운 일: " + ", ".join(f"{e['title']}({dday(dparse(e['date']))})" for e in soon) + ".")
    doing = [e for e in todo_items() if e["status"] == "진행 중"]
    if doing:
        parts.append(f"지난번에 시작한 **{doing[0]['title']}**, 어디까지 진행했나요?")
    parts.append("오늘 새로 등록할 과제나 일정이 있나요?")
    return " ".join(parts)


def ensure_greeting():
    key = today().isoformat()
    if st.session_state.greeted != key:
        say("assistant", greeting(), daily=True)
        st.session_state.greeted = key


# ─────────────────────────────────────────────────────────────
# 로그인(구글)과 저장(Supabase) · Secrets에 값이 있을 때만 동작
# ─────────────────────────────────────────────────────────────
SAVE_KEYS = ["onboarded", "profile", "events", "messages", "candidates", "greeted",
             "stages", "plan_done", "tt_rows", "study_id"]


def auth_on():
    try:
        a = st.secrets.get("auth", None)
        return bool(a and a.get("client_id") and a.get("client_secret"))
    except Exception:
        return False


def logged_in():
    if not auth_on():
        return False
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


def user_email():
    try:
        return str(getattr(st.user, "email", "") or "").strip().lower()
    except Exception:
        return ""


def user_name():
    try:
        return str(getattr(st.user, "given_name", "") or getattr(st.user, "name", "") or "").strip()
    except Exception:
        return ""


def store_on():
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_KEY"))


def _sb(method, params=None, body=None, prefer=""):
    key = _secret("SUPABASE_KEY")
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    url = _secret("SUPABASE_URL").rstrip("/") + "/rest/v1/campus_mate"
    return requests.request(method, url, headers=headers, params=params, json=body, timeout=20)


def load_user():
    """로그인 직후 한 번, 저장해 둔 내 정보를 불러온다."""
    ss = st.session_state
    email = user_email()
    if not email or ss.get("loaded_for") == email:
        return
    ss.loaded_for = email
    ss.store_ok = False
    if not store_on():
        return
    if _bad_key(_secret("SUPABASE_KEY")) or _bad_key(_secret("SUPABASE_URL")):
        ss.store_msg = "Secrets의 SUPABASE_URL 또는 SUPABASE_KEY 값이 올바르지 않아요. 이번에는 저장되지 않아요."
        return
    try:
        r = _sb("GET", params={"email": f"eq.{email}", "select": "data"})
    except Exception as e:
        ss.store_msg = f"저장소에 연결하지 못했어요 ({type(e).__name__}). 이번에는 저장되지 않아요."
        return
    if r.status_code != 200:
        ss.store_msg = f"저장소에서 내 정보를 불러오지 못했어요 (코드 {r.status_code}). 이번에는 저장되지 않아요."
        return
    ss.store_ok = True
    rows = r.json()
    data = rows[0].get("data") if rows else None
    if isinstance(data, dict) and data:
        for k in SAVE_KEYS:
            if k in data:
                ss[k] = data[k]
        ss.stages = {int(k): bool(v) for k, v in (ss.get("stages") or {}).items()}
        for n in (3, 2, 1, 0):
            ss.stages.setdefault(n, True)
        ss.saved_sig = hashlib.md5(json.dumps({k: ss.get(k) for k in SAVE_KEYS}, sort_keys=True,
                                              ensure_ascii=False, default=str).encode()).hexdigest()
        ss.page = "대화"


def save_user():
    """바뀐 내용이 있을 때만 저장한다."""
    ss = st.session_state
    if not logged_in() or not ss.get("store_ok"):
        return
    snap = {k: ss.get(k) for k in SAVE_KEYS}
    snap["messages"] = (snap.get("messages") or [])[-80:]
    raw = json.dumps(snap, sort_keys=True, ensure_ascii=False, default=str)
    sig = hashlib.md5(raw.encode()).hexdigest()
    if ss.get("saved_sig") == sig:
        return
    try:
        r = _sb("POST", params={"on_conflict": "email"},
                body=[{"email": user_email(), "data": json.loads(raw), "updated_at": now().isoformat()}],
                prefer="resolution=merge-duplicates,return=minimal")
        if r.status_code in (200, 201, 204):
            ss.saved_sig = sig
            ss.store_msg = ""
        else:
            ss.store_msg = f"저장하지 못했어요 (코드 {r.status_code})."
    except Exception:
        ss.store_msg = "저장소에 연결하지 못했어요."


def enter_guest():
    st.session_state.guest = True


def leave_guest():
    st.session_state.guest = False


def page_login():
    left, right = st.columns([5, 4], gap="large")
    with left:
        H('<div class="cm-brand"><div class="cm-logo"></div><div><b>Campus Mate</b>'
          '<span>말하면 정리되는 캠퍼스 일정</span></div></div>')
        H('<h1 class="cm-h1">공지는 캡처하고, 일정은 말로.<br><mark>캘린더는 알아서 채워져요.</mark></h1>'
          '<p class="cm-lead">로그인하면 시간표와 일정이 저장돼서, 다음에 들어와도 그대로 이어져요.</p>')
        a, b, _ = st.columns([2, 2, 2])
        a.button("Google로 로그인", type="primary", on_click=st.login, width="stretch")
        b.button("로그인 없이 둘러보기", on_click=enter_guest, width="stretch")
        H('<p class="cm-note">로그인에는 구글 계정의 이름과 이메일만 사용해요. '
          '둘러보기로 들어가면 창을 닫을 때 내용이 사라져요.</p>')
    with right:
        t = today() + timedelta(days=5)
        H('<div style="height:54px"></div><div class="cm-cand" style="max-width:420px">' + chip("과제") +
          '<div class="b">유통경로관리 중간보고서</div><dl>'
          f'<dt>마감</dt><dd>{fmt_date(t)} 23:59</dd><dt>제출</dt><dd>LMS 과제함 PDF</dd>'
          f'<dt>알림</dt><dd>{fmt_date(t - timedelta(days=3))}부터 매일</dd></dl>'
          '<div class="cm-ok" style="margin-top:10px">캘린더에 등록됨</div></div>')


# ─────────────────────────────────────────────────────────────
# 상태 초기화
# ─────────────────────────────────────────────────────────────
def init():
    ss = st.session_state
    ss.setdefault("onboarded", False)
    ss.setdefault("ob_step", 1)
    ss.setdefault("page", "대화")
    ss.setdefault("profile", {"name": "", "school": "", "major": "", "grade": "", "kind": "한국인 학생",
                              "nation": "", "lang": "한국어"})
    ss.setdefault("events", [])
    ss.setdefault("messages", [])
    ss.setdefault("candidates", {})
    ss.setdefault("greeted", "")
    ss.setdefault("stages", {3: True, 2: True, 1: True, 0: True})
    ss.setdefault("study_id", "")
    ss.setdefault("plan_done", {})
    ss.setdefault("cal_ym", (today().year, today().month))
    ss.setdefault("tt_rows", None)


def finish_onboarding(with_samples=True):
    ss = st.session_state
    rows = ss.tt_rows if ss.tt_rows is not None else SAMPLE_TIMETABLE
    ss.events = academic_events(ss.profile["school"]) + class_events(rows)
    if with_samples:
        ss.events += sample_tasks()
    ss.messages, ss.candidates, ss.greeted = [], {}, ""
    ss.onboarded = True
    ss.page = "대화"


def quick_start():
    st.session_state.profile = {"name": "서현", "school": "세종대학교", "major": "경영학부", "grade": "3학년",
                                "kind": "한국인 학생", "nation": "", "lang": "한국어"}
    st.session_state.tt_rows = None
    finish_onboarding(True)


def reset_all():
    keep = {k: st.session_state[k] for k in ("guest", "loaded_for", "store_ok") if k in st.session_state}
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    for k, v in keep.items():
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────
# 화면: 시작하기 (회원가입 → 학사일정·시간표 → 확인)
# ─────────────────────────────────────────────────────────────
def page_onboarding():
    ss = st.session_state
    step = ss.ob_step
    left, right = st.columns([5, 4], gap="large")
    with left:
        H('<div class="cm-brand"><div class="cm-logo"></div><div><b>Campus Mate</b>'
          '<span>말하면 정리되는 캠퍼스 일정</span></div></div>')
        H('<h1 class="cm-h1">공지는 캡처하고, 일정은 말로.<br><mark>캘린더는 알아서 채워져요.</mark></h1>'
          '<p class="cm-lead">LMS 공지, 단톡방, 강의계획서에 흩어진 과제와 시험을 대화 한 번으로 모으고, '
          '마감 3일 전부터 챙겨 주고, 시작할 땐 같이 공부해요. 유학생에게는 전공 용어를 모국어로 풀어 줘요.</p>')
        labels = ["내 정보", "학사일정·시간표", "확인"]
        H('<ol class="cm-steps">' + "".join(
            f'<li class="{"on" if i + 1 == step else ("done" if i + 1 < step else "")}">{l}</li>'
            for i, l in enumerate(labels)) + "</ol>")

        if step == 1:
            p = ss.profile
            a, b = st.columns(2)
            name = a.text_input("이름 또는 닉네임", value=p["name"] or user_name(), placeholder="예: 서현")
            school = b.selectbox("학교", SCHOOLS, index=SCHOOLS.index(p["school"]) if p["school"] in SCHOOLS else 0)
            a, b = st.columns(2)
            major = a.text_input("전공·학과", value=p["major"], placeholder="예: 경영학부")
            grades = ["1학년", "2학년", "3학년", "4학년", "대학원"]
            grade = b.selectbox("학년", grades, index=grades.index(p["grade"]) if p["grade"] in grades else 0)
            kind = st.radio("구분", ["한국인 학생", "외국인 유학생"], horizontal=True,
                            index=0 if p["kind"] == "한국인 학생" else 1)
            nation, lang = "", "한국어"
            if kind == "외국인 유학생":
                a, b = st.columns(2)
                nation = a.text_input("국적", value=p["nation"], placeholder="예: 일본")
                lang = b.selectbox("용어 해설을 받을 언어", ["English", "日本語", "中文"])
            H('<p class="cm-note">생년월일은 받지 않아요. 일정 관리에 필요한 정보만 물어봅니다.</p>')
            if st.button("다음: 학사일정 불러오기", type="primary"):
                if not name.strip():
                    st.error("이름이나 닉네임을 입력해 주세요.")
                else:
                    ss.profile = {"name": name.strip(), "school": school, "major": major.strip(),
                                  "grade": grade, "kind": kind, "nation": nation.strip(), "lang": lang}
                    ss.ob_step = 2
                    st.rerun()

        elif step == 2:
            school = ss.profile["school"]
            acad = academic_events(school)
            H(f'<div class="cm-h2">{esc(school)} 학사일정 {len(acad)}건을 불러왔어요 '
              '<span class="cm-demo">데모용 예시 일정</span></div>')
            H("".join(
                f'<div class="cm-row"><div class="t" style="width:150px">{fmt_date(dparse(e["date"]))}'
                + (f' ~ {dparse(e["end"]).month}/{dparse(e["end"]).day}' if e["end"] else "")
                + f'</div><div><div class="b">{esc(e["title"])}</div></div></div>' for e in acad))
            st.write("")
            H('<div class="cm-h2">에브리타임 시간표 캡처를 올려 주세요</div>')
            up = st.file_uploader("시간표 캡처", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
            if up is not None and ai_ready():
                raw = up.getvalue()
                sig = hashlib.md5(raw).hexdigest()
                if ss.get("tt_sig") != sig:
                    with st.spinner("시간표를 읽고 있어요"):
                        rows, err = read_timetable(raw, getattr(up, "type", "") or "image/png")
                    ss.tt_sig = sig
                    ss.tt_msg = err or f"수업 {len(rows)}건을 읽었어요. 틀린 곳이 있으면 아래 표에서 고쳐 주세요."
                    ss.tt_ok = not err
                    if not err:
                        ss.tt_rows = rows
                        ss.tt_ver = ss.get("tt_ver", 0) + 1
                (st.success if ss.get("tt_ok") else st.warning)(ss.get("tt_msg", ""))
            elif up is not None:
                st.info("AI 키가 연결되지 않아 이미지를 읽지 못했어요. 아래 예시 표를 내 시간표에 맞게 고쳐 쓰면 돼요.")
            if ai_ready():
                H('<p class="cm-note">캡처를 올리면 AI가 수업을 읽어 아래 표를 채워요. 캡처가 없으면 예시 표를 고쳐 써도 돼요. '
                  '칸을 눌러 고치거나 맨 아래 줄에 수업을 추가할 수 있어요.</p>')
            else:
                H('<p class="cm-note">캡처가 없어도 괜찮아요. 아래 표가 인식 결과 예시예요. '
                  '칸을 눌러 고치거나 맨 아래 줄에 수업을 추가할 수 있어요.</p>')
            edited = st.data_editor(
                ss.tt_rows if ss.tt_rows is not None else SAMPLE_TIMETABLE,
                num_rows="dynamic", hide_index=True, key=f"tt_editor_{ss.get('tt_ver', 0)}",
                column_config={"요일": st.column_config.SelectboxColumn("요일", options=DAYS + [ONLINE], required=True,
                                                                     help="시간이 정해지지 않은 온라인 강의는 ‘온라인’을 고르세요."),
                               "시작": st.column_config.TextColumn("시작", help="예: 10:30"),
                               "종료": st.column_config.TextColumn("종료", help="예: 12:00")})
            a, b, _ = st.columns([1, 2, 3])
            if a.button("이전"):
                ss.ob_step = 1
                st.rerun()
            if b.button("다음: 확인하기", type="primary"):
                rows = edited if isinstance(edited, list) else edited.to_dict("records")
                ss.tt_rows = [r for r in rows if str(r.get("강의명") or "").strip()]
                ss.ob_step = 3
                st.rerun()

        else:
            p = ss.profile
            rows = ss.tt_rows if ss.tt_rows is not None else SAMPLE_TIMETABLE
            names = []
            for r in rows:
                if r["강의명"] not in names:
                    names.append(r["강의명"])
            who = f'{p["school"]} {p["major"]} {p["grade"]}'.strip()
            extra = f' · {p["nation"]} · 해설 언어 {p["lang"]}' if p["kind"] == "외국인 유학생" else ""
            H(f'<div class="cm-cand"><div class="b">{esc(p["name"])}님의 캠퍼스</div><dl>'
              f'<dt>소속</dt><dd>{esc(who)}{esc(extra)}</dd>'
              f'<dt>학사일정</dt><dd>{len(academic_events(p["school"]))}건 등록 예정</dd>'
              f'<dt>수업</dt><dd>{esc(", ".join(names))} (매주 반복 {len([r for r in rows if r.get("요일") in DAYS])}건)</dd>'
              '<dt>알림</dt><dd>마감 3일 전, 2일 전, 1일 전, 당일</dd></dl></div>')
            with_s = st.checkbox("예시 과제와 팀플도 넣어서 둘러보기", value=True,
                                 help="알림과 함께 학습 기능을 바로 볼 수 있어요. 설정에서 언제든 지울 수 있어요.")
            a, b, _ = st.columns([1, 2, 3])
            if a.button("이전"):
                ss.ob_step = 2
                st.rerun()
            if b.button("Campus Mate 시작하기", type="primary"):
                finish_onboarding(with_s)
                st.rerun()

    with right:
        t = today() + timedelta(days=5)
        H('<div style="height:54px"></div>'
          '<div class="cm-shot" style="margin-left:auto"><div class="bar"><span>LMS 공지사항</span><span>캡처</span></div>'
          '<b>[유통경로관리] 중간보고서 제출 안내</b><br>'
          f'제출 기한: <span class="cm-mark">{t.month}월 {t.day}일({DAYS[t.weekday()]}) 23:59</span><br>'
          '제출 방식: <span class="cm-mark">LMS 과제함 PDF</span><br>분량: A4 5매 이내</div>'
          '<div style="height:14px"></div>'
          '<div class="cm-cand" style="max-width:420px">' + chip("과제") +
          '<div class="b">유통경로관리 중간보고서</div><dl>'
          f'<dt>마감</dt><dd>{fmt_date(t)} 23:59</dd><dt>제출</dt><dd>LMS 과제함 PDF</dd>'
          f'<dt>알림</dt><dd>{fmt_date(t - timedelta(days=3))}부터 매일</dd></dl>'
          '<div class="cm-ok" style="margin-top:10px">캘린더에 등록됨</div></div>')
        st.write("")
        H('<p class="cm-note" style="max-width:420px">가입 없이 먼저 보고 싶다면 예시 프로필로 바로 들어가 보세요.</p>')
        st.button("예시 프로필로 바로 둘러보기", on_click=quick_start)


# ─────────────────────────────────────────────────────────────
# 화면: 오늘 (대화)
# ─────────────────────────────────────────────────────────────
def candidate_card(c):
    d = dparse(c["date"])
    rows = [("과목", c["course"] or "미지정"), ("날짜", f"{fmt_date(d)} {c['time']}".strip())]
    if c["location"]:
        rows.append(("장소", c["location"]))
    for line in (c["details"] or "").split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            rows.append((k.strip(), v.strip()))
    H('<div class="cm-cand">' + chip(c["category"]) + f'<div class="b">{esc(c["title"])}</div><dl>'
      + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in rows) + "</dl>"
      + ('<div class="cm-ok" style="margin-top:10px">캘린더에 등록됨</div>' if c["state"] == "등록됨" else "")
      + ('<div class="cm-note" style="margin-top:10px">등록하지 않았어요.</div>' if c["state"] == "취소" else "")
      + "</div>")
    if c["state"] != "확인 필요":
        return
    dup = find_dup(c)
    if dup:
        st.warning(f"같은 날에 비슷한 일정이 이미 있어요: {dup['title']}. 새로 추가하는 대신 기존 일정을 고칠 수 있어요.")
    a, b, d3, _ = st.columns([2.2, 1.3, 1.3, 3])
    if a.button("캘린더에 등록", key="ok_" + c["id"], type="primary"):
        register(c)
        st.rerun()
    with b.popover("수정"):
        with st.form("f_" + c["id"]):
            title = st.text_input("일정 이름", value=c["title"])
            cat = st.selectbox("구분", CATS, index=CATS.index(c["category"]))
            opts = ["미지정"] + courses()
            course = st.selectbox("과목", opts, index=opts.index(c["course"]) if c["course"] in opts else 0)
            day = st.date_input("날짜", value=d or today())
            tm = st.text_input("시간", value=c["time"], placeholder="예: 23:59")
            det = st.text_area("메모", value=c["details"], height=80)
            if st.form_submit_button("고치기", type="primary"):
                c.update(title=title.strip() or c["title"], category=cat,
                         course="" if course == "미지정" else course, date=day.isoformat(),
                         time=parse_time(tm)[0] if tm.strip() else "", details=det.strip())
                st.rerun()
    if d3.button("버리기", key="no_" + c["id"]):
        c["state"] = "취소"
        st.rerun()


def register(c):
    e = new_event(c["title"], c["category"], dparse(c["date"]), time=c["time"], course=c["course"],
                  location=c["location"], details=c["details"], source=c["source"])
    st.session_state.events.append(e)
    c["state"] = "등록됨"
    if c["category"] in ("과제", "시험"):
        first = dparse(c["date"]) - timedelta(days=3)
        say("assistant", f"등록했어요. {fmt_date(first)}부터 마감일까지 매일 알려 드릴게요. "
            "시작하고 싶을 때 “이 과제 시작할래”라고 말해 주세요.")
    else:
        say("assistant", "캘린더에 등록했어요.")


def shot_html():
    n = notice_sample()
    return ('<div class="cm-shot"><div class="bar"><span>LMS 공지사항</span><span>예시 캡처</span></div>'
            f'<b>[{n["course"]}] {n["title"]}</b><br>제출 기한: {n["date"].month}월 {n["date"].day}일'
            f'({DAYS[n["date"].weekday()]}) {n["time"]}<br>제출 방식: {n["how"]}<br>분량: {n["size"]}</div>')


def ex_capture():
    say("user", "이 공지 캡처 등록해 줘", shot=True)
    respond_to_capture()


def ex_text():
    msg = "다음 주 수요일 오후 2시에 유통 팀플 회의 있어"
    say("user", msg)
    respond(msg)


def ex_start():
    msg = "이 과제 이제 시작할래!"
    say("user", msg)
    respond(msg)


def ex_term():
    msg = "경로 갈등이 무슨 뜻이야?"
    say("user", msg)
    respond(msg)


def page_chat():
    ss = st.session_state
    ensure_greeting()
    H('<h1 class="cm-h1">무엇이든 <mark>말로 정리해요</mark></h1>'
      '<p class="cm-lead">과제나 일정이 생기면 말하거나 공지 캡처를 올려 주세요. 확인만 하면 캘린더에 들어가요.</p>')
    for m in ss.messages:
        with st.chat_message(m["role"], avatar="📎" if m["role"] == "assistant" else "🙂"):
            if m.get("shot"):
                H(shot_html())
            st.markdown(m["content"])
            if m.get("cand") and m["cand"] in ss.candidates:
                candidate_card(ss.candidates[m["cand"]])
            if m.get("study") and get_event(m["study"]):
                if st.button("함께 학습 열기", key="st_" + m["id"], type="primary"):
                    go("함께 학습", study_id=m["study"])
                    st.rerun()
    H('<p class="cm-note" style="margin:14px 0 6px">이렇게 말해 보세요</p>')
    a, b, c, d, _ = st.columns([1, 1, 1, 1, 1.6])
    a.button("공지 캡처 올리기", on_click=ex_capture, width="stretch")
    b.button("말로 일정 등록", on_click=ex_text, width="stretch")
    c.button("과제 시작할래", on_click=ex_start, width="stretch")
    d.button("용어 물어보기", on_click=ex_term, width="stretch")

    prompt = st.chat_input("예: 금요일까지 소비자행동론 레포트 제출 (공지 캡처도 첨부할 수 있어요)",
                           accept_file=True, file_type=["png", "jpg", "jpeg", "pdf"])
    if prompt:
        text = (getattr(prompt, "text", None) or (prompt if isinstance(prompt, str) else "")).strip()
        files = getattr(prompt, "files", None) or []
        if files:
            say("user", (text + "\n\n" if text else "") + f"첨부: {files[0].name}")
            respond_to_capture(files[0])
        elif text:
            say("user", text)
            respond(text)
        st.rerun()


def page_today():
    t = today()
    al = alerts()
    H(f'<h1 class="cm-h1">{t.month}월 {t.day}일 {DAYS[t.weekday()]}요일, <mark>챙길 일 {len(al)}건</mark></h1>'
      '<p class="cm-lead">마감이 3일 안으로 들어온 일과 오늘 일정을 한눈에 봐요.</p>')
    left, right = st.columns([6, 5], gap="large")
    with left:
        H('<div class="cm-h2">마감 알림</div>')
        if not al:
            H('<div class="cm-empty">마감 3일 안에 들어온 과제나 시험이 없어요.</div>')
        for e, k, title, sub in al:
            H(f'<div class="cm-alert"><div class="k">{esc(k)} · {esc(title)}</div>'
              f'<div class="b">{esc(e["course"])} {esc(e["title"])}</div>'
              f'<div class="s">{fmt_date(dparse(e["date"]))} {esc(e["time"])} 마감. {esc(sub)}</div></div>')
            a, b, _ = st.columns([1.3, 1.3, 2])
            if a.button("같이 시작하기" if e["status"] == "시작 전" else "이어서 하기", key="al_s_" + e["id"], width="stretch"):
                if e["status"] == "시작 전":
                    e["status"] = "진행 중"
                go("함께 학습", study_id=e["id"])
                st.rerun()
            if b.button("제출했어요", key="al_d_" + e["id"], width="stretch"):
                e["status"] = "완료"
                st.rerun()
            st.write("")
    with right:
        H('<div class="cm-h2">오늘 일정</div>')
        items = events_on(t)
        if not items:
            H('<div class="cm-empty">오늘은 등록된 일정이 없어요.</div>')
        else:
            H("".join(
                f'<div class="cm-row"><div class="t">{esc(e["time"] or "종일")}</div>'
                f'<div class="bar" style="background:{CAT_COLOR[e["category"]]}"></div>'
                f'<div><div class="b">{esc(e["title"])}</div>'
                f'<div class="s">{esc(e["category"])}{" · " + esc(e["location"]) if e["location"] else ""}</div></div></div>'
                for e in items))
        st.write("")
        H('<div class="cm-h2">내일 일정</div>')
        items = events_on(t + timedelta(days=1))
        if not items:
            H('<div class="cm-empty">내일은 등록된 일정이 없어요.</div>')
        else:
            H("".join(
                f'<div class="cm-row"><div class="t">{esc(e["time"] or "종일")}</div>'
                f'<div class="bar" style="background:{CAT_COLOR[e["category"]]}"></div>'
                f'<div><div class="b">{esc(e["title"])}</div>'
                f'<div class="s">{esc(e["category"])}{" · " + esc(e["location"]) if e["location"] else ""}</div></div></div>'
                for e in items))
        st.write("")
        st.button("새 일정은 대화로 등록하기", on_click=go, args=("대화",))


# ─────────────────────────────────────────────────────────────
# 화면: 캘린더
# ─────────────────────────────────────────────────────────────
def ics_text():
    def stamp(d, tm):
        if tm:
            return f"{d.strftime('%Y%m%d')}T{tm.replace(':', '')}00"
        return d.strftime("%Y%m%d")

    def clean(s):
        return str(s).replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")

    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Campus Mate//Demo//KO", "CALSCALE:GREGORIAN",
         "X-WR-CALNAME:Campus Mate", "X-WR-TIMEZONE:Asia/Seoul"]
    for e in st.session_state.events:
        d = dparse(e["date"])
        if not d:
            continue
        L += ["BEGIN:VEVENT", f"UID:{e['id']}@campusmate", f"DTSTAMP:{now().strftime('%Y%m%dT%H%M%S')}",
              f"SUMMARY:{clean(('[' + e['category'] + '] ') + e['title'])}"]
        if e["time"]:
            L.append(f"DTSTART;TZID=Asia/Seoul:{stamp(d, e['time'])}")
            if e["end_time"]:
                L.append(f"DTEND;TZID=Asia/Seoul:{stamp(d, e['end_time'])}")
        else:
            end = (dparse(e["end"]) or d) + timedelta(days=1)
            L += [f"DTSTART;VALUE=DATE:{stamp(d, '')}", f"DTEND;VALUE=DATE:{stamp(end, '')}"]
        if e["weekly"]:
            u = dparse(e["until"])
            L.append("RRULE:FREQ=WEEKLY" + (f";UNTIL={u.strftime('%Y%m%d')}T145959Z" if u else ""))
        if e["location"]:
            L.append(f"LOCATION:{clean(e['location'])}")
        if e["details"]:
            L.append(f"DESCRIPTION:{clean(e['details'])}")
        if e["category"] in ("과제", "시험"):
            for n in (3, 2, 1):
                L += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{clean(e['title'])}",
                      f"TRIGGER:-P{n}D", "END:VALARM"]
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(L)


def move_month(delta):
    y, m = st.session_state.cal_ym
    m += delta
    if m < 1:
        y, m = y - 1, 12
    elif m > 12:
        y, m = y + 1, 1
    st.session_state.cal_ym = (y, m)


def this_month():
    st.session_state.cal_ym = (today().year, today().month)


def page_calendar():
    ss = st.session_state
    y, m = ss.cal_ym
    H(f'<h1 class="cm-h1">{y}년 <mark>{m}월</mark></h1>')
    a, b, c, d, e5 = st.columns([1, 1, 1, 2.2, 4])
    a.button("이전 달", on_click=move_month, args=(-1,), width="stretch")
    b.button("이번 달", on_click=this_month, width="stretch")
    c.button("다음 달", on_click=move_month, args=(1,), width="stretch")
    show_cls = d.toggle("수업도 표시", value=False)
    grid, side = st.columns([8, 3.4], gap="large")
    with grid:
        cells = "".join(f'<div class="hd">{x}</div>' for x in DAYS)
        for week in pycal.Calendar(firstweekday=0).monthdatescalendar(y, m):
            for day in week:
                cls = "c" + ("" if day.month == m else " out") + (" today" if day == today() else "")
                items = events_on(day, include_classes=show_cls)
                chips = ""
                for ev in items[:3]:
                    col = CAT_COLOR[ev["category"]]
                    done = "text-decoration:line-through;opacity:.55;" if ev["status"] == "완료" and ev["category"] in ("과제", "시험") else ""
                    chips += f'<span class="e" style="background:{col}1F;color:{col};{done}">{esc(ev["title"])}</span>'
                if len(items) > 3:
                    chips += f'<div class="more">+{len(items) - 3}개 더</div>'
                cells += f'<div class="{cls}"><span class="n">{day.day}</span>{chips}</div>'
        H(f'<div class="cm-cal">{cells}</div>')
        H('<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap">' + "".join(chip(x) for x in CATS) + "</div>")
    with side:
        base = today() if (y, m) == (today().year, today().month) else date(y, m, 1)
        sel = st.date_input("날짜 선택", value=base, key=f"sel_{y}_{m}")
        H(f'<div class="cm-h2">{fmt_date(sel)}</div>')
        items = events_on(sel)
        if not items:
            H('<div class="cm-empty">이 날은 일정이 없어요.</div>')
        for ev in items:
            H(f'<div class="cm-row"><div class="t">{esc(ev["time"] or "종일")}</div>'
              f'<div class="bar" style="background:{CAT_COLOR[ev["category"]]}"></div>'
              f'<div><div class="b">{esc(ev["title"])}</div><div class="s">{esc(ev["category"])}'
              f'{" · " + esc(ev["location"]) if ev["location"] else ""}{" · " + esc(ev["source"]) if ev["source"] else ""}</div></div></div>')
            if not ev["weekly"] and ev["category"] != "학사":
                if st.button("이 일정 삭제", key="del_" + ev["id"] + sel.isoformat(), type="tertiary"):
                    ss.events = [x for x in ss.events if x["id"] != ev["id"]]
                    st.rerun()
        st.write("")
        with st.expander("일정 직접 추가"):
            with st.form("add_ev", clear_on_submit=True):
                title = st.text_input("일정 이름")
                cat = st.selectbox("구분", CATS[:3] + ["기타"])
                opts = ["미지정"] + courses()
                course = st.selectbox("과목", opts)
                tm = st.text_input("시간", placeholder="예: 14:30")
                det = st.text_area("메모", height=70)
                if st.form_submit_button("추가", type="primary") and title.strip():
                    ss.events.append(new_event(title.strip(), cat, sel, time=parse_time(tm)[0] if tm.strip() else "",
                                               course="" if course == "미지정" else course, details=det.strip()))
                    st.rerun()
        st.download_button("캘린더 파일(.ics) 내려받기", data=ics_text().encode("utf-8"),
                           file_name="campus_mate.ics", mime="text/calendar", width="stretch")
        H('<p class="cm-note">내려받은 파일을 구글 캘린더나 애플 캘린더의 “가져오기”에 넣으면 일정과 3일 전 알림이 그대로 들어가요.</p>')


# ─────────────────────────────────────────────────────────────
# 화면: 시간표
# ─────────────────────────────────────────────────────────────
def _mins(s):
    try:
        h, m = str(s).split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def page_timetable():
    cls = [e for e in st.session_state.events if e["category"] == "수업" and e["weekly"]]
    online = [e for e in st.session_state.events if e["category"] == "수업" and not e["weekly"] and not e["date"]]
    H('<h1 class="cm-h1">이번 학기 <mark>시간표</mark></h1>'
      '<p class="cm-lead">캡처에서 읽어 온 수업이 매주 반복 일정으로 등록돼 있어요.</p>')
    if not cls and not online:
        st.info("등록된 수업이 없어요. 설정에서 처음부터 다시 시작하면 시간표를 등록할 수 있어요.")
        return
    names = courses()
    starts = [_mins(e["time"]) for e in cls if _mins(e["time"]) is not None]
    ends = [_mins(e["end_time"]) for e in cls if _mins(e["end_time"]) is not None]
    h0 = min(9, (min(starts) // 60) if starts else 9)
    h1 = max(18, -(-max(ends) // 60) if ends else 18)
    wd = today().weekday()
    out = '<div class="cm-tt"><div class="hd"></div>' + "".join(
        f'<div class="hd{" on" if i == wd else ""}">{DAYS[i]}</div>' for i in range(5))
    out += '<div class="hours">' + "".join(f"<div>{h}</div>" for h in range(h0, h1)) + "</div>"
    for i in range(5):
        blocks = ""
        for e in cls:
            d0 = dparse(e["date"])
            s, en = _mins(e["time"]), _mins(e["end_time"])
            if not d0 or d0.weekday() != i or s is None:
                continue
            en = en if en and en > s else s + 60
            bg, fg = BLOCK_COLORS[names.index(e["course"]) % len(BLOCK_COLORS)] if e["course"] in names else BLOCK_COLORS[0]
            blocks += (f'<div class="blk" style="top:{s - h0 * 60}px;height:{en - s - 3}px;background:{bg};color:{fg}">'
                       f'<b>{esc(e["title"])}</b><span>{esc(e["time"])}~{esc(e["end_time"])} {esc(e["location"])}</span></div>')
        out += f'<div class="col" style="height:{(h1 - h0) * 60}px">{blocks}</div>'
    H(out + "</div>")
    if online:
        H('<div class="cm-h2" style="margin-top:20px">온라인 강의</div>' + "".join(
            f'<div class="cm-row"><div class="bar" style="background:{CAT_COLOR["수업"]}"></div>'
            f'<div><div class="b">{esc(e["title"])}</div><div class="s">정해진 시간 없이 듣는 강의</div></div></div>'
            for e in online))
    st.write("")
    total = sum((_mins(e["end_time"]) or 0) - (_mins(e["time"]) or 0) for e in cls)
    H(f'<p class="cm-note">{len(names)}과목, 주 {len(cls)}회, 주당 수업 {total // 60}시간 {total % 60:02d}분</p>')


# ─────────────────────────────────────────────────────────────
# 화면: 과제·시험
# ─────────────────────────────────────────────────────────────
def task_card(e):
    d = dparse(e["date"])
    n = (d - today()).days
    cls = "done" if e["status"] == "완료" else ("hot" if n <= 1 else "")
    track = ""
    if e["status"] != "완료":
        seg = ""
        for k in (3, 2, 1, 0):
            seg += f'<i class="{"now" if n == k else ("on" if n < k else "")}" title="{STAGES[k][0]}: {STAGES[k][1]}"></i>'
        track = f'<div class="cm-track">{seg}</div>'
    H(f'<div class="cm-task"><div class="top">{chip(e["category"])}<span class="cm-dday {cls}">{dday(d)}</span></div>'
      f'<div class="b">{esc(e["title"])}</div>'
      f'<div class="s">{esc(e["course"] or "과목 미지정")} · {fmt_date(d)} {esc(e["time"])}</div>{track}</div>')
    a, b, c = st.columns([1.2, 1.2, 0.8])
    if e["status"] == "시작 전":
        if a.button("시작", key="s_" + e["id"], width="stretch"):
            e["status"] = "진행 중"
            st.rerun()
    elif e["status"] == "진행 중":
        if a.button("완료", key="d_" + e["id"], width="stretch"):
            e["status"] = "완료"
            st.rerun()
    else:
        if a.button("되돌리기", key="u_" + e["id"], width="stretch"):
            e["status"] = "진행 중"
            st.rerun()
    if e["status"] != "완료":
        if b.button("함께 학습", key="g_" + e["id"], width="stretch"):
            if e["status"] == "시작 전":
                e["status"] = "진행 중"
            go("함께 학습", study_id=e["id"])
            st.rerun()
    with c.popover("더보기"):
        st.caption(e["details"] or "메모가 없어요.")
        st.caption(f"등록 경로: {e['source']}")
        if st.button("삭제", key="x_" + e["id"]):
            st.session_state.events = [x for x in st.session_state.events if x["id"] != e["id"]]
            st.rerun()


def page_tasks():
    items = todo_items()
    left = len([e for e in items if e["status"] != "완료"])
    H(f'<h1 class="cm-h1">끝내야 할 일 <mark>{left}개</mark></h1>'
      '<p class="cm-lead">막대 네 칸은 마감 3일 전, 2일 전, 1일 전, 당일 알림이에요. 지나간 알림은 노란색, 오늘 알림은 분홍색으로 보여요.</p>')
    if not items:
        st.info("등록된 과제나 시험이 없어요. ‘대화’ 화면에서 말로 등록해 보세요.")
        return
    cols = st.columns(3, gap="medium")
    for col, status in zip(cols, STATUS):
        group = [e for e in items if e["status"] == status]
        with col:
            H(f'<div class="cm-colhd">{status} <em>{len(group)}</em></div>')
            if not group:
                H('<div class="cm-empty">비어 있어요.</div>')
            for e in group:
                task_card(e)


# ─────────────────────────────────────────────────────────────
# 화면: 함께 학습
# ─────────────────────────────────────────────────────────────
def draft_feedback(text, terms):
    body = text.strip()
    chars = len(re.sub(r"\s", "", body))
    paras = [p for p in re.split(r"\n\s*\n|\n", body) if p.strip()]
    sents = [s for s in re.split(r"(?<=[.!?。다요])\s+", body) if s.strip()]
    avg = (sum(len(s) for s in sents) / len(sents)) if sents else 0
    used = [t for t in terms if t in body]
    cited = bool(re.search(r"\(\d{4}\)|\d{4}\)|출처|참고문헌|https?://", body))
    res = [(chars >= 300, f"분량: 공백 제외 {chars}자" + ("" if chars >= 300 else ". 아직 짧아요. 주장마다 근거 문장을 하나씩 더해 보세요.")),
           (len(paras) >= 3, f"구성: {len(paras)}문단" + ("" if len(paras) >= 3 else ". 서론, 본론, 결론이 나뉘도록 문단을 나눠 보세요.")),
           (0 < avg <= 70, f"문장 길이: 평균 {avg:.0f}자" + ("" if 0 < avg <= 70 else ". 긴 문장은 두 개로 나누면 읽기 쉬워요.")),
           (bool(used), ("수업 용어 사용: " + ", ".join(used)) if used else "수업 용어: 수업에서 배운 개념어가 보이지 않아요. 용어 탭의 개념을 연결해 보세요."),
           (cited, "출처 표기: 있어요" if cited else "출처 표기: 찾지 못했어요. 인용한 자료의 저자와 연도를 적어 주세요.")]
    return res


def page_study():
    ss = st.session_state
    todo = [e for e in todo_items() if e["status"] != "완료"]
    H('<h1 class="cm-h1">같이 하면 <mark>시작이 쉬워요</mark></h1>')
    if not todo:
        st.info("진행할 과제나 시험이 없어요. ‘대화’ 화면에서 일정을 먼저 등록해 주세요.")
        return
    ids = [e["id"] for e in todo]
    idx = ids.index(ss.study_id) if ss.study_id in ids else 0
    pick = st.selectbox("무엇을 할까요?", ids, index=idx,
                        format_func=lambda i: f"{get_event(i)['course']} {get_event(i)['title']} ({dday(dparse(get_event(i)['date']))})")
    ss.study_id = pick
    e = get_event(pick)
    d = dparse(e["date"])
    k = lang_key()
    terms = GLOSSARY.get(e["course"], [])
    all_terms = terms or [g for v in GLOSSARY.values() for g in v]
    H(f'<p class="cm-lead">{chip(e["category"])} &nbsp;<b>{esc(e["course"])} {esc(e["title"])}</b> · '
      f'{fmt_date(d)} {esc(e["time"])} 마감 · <span class="cm-dday">{dday(d)}</span></p>')
    H('<span class="cm-demo">데모 안내</span> <span class="cm-note">이 화면의 분석과 제안은 미리 준비한 규칙과 예시 자료로 만들어져요. '
      '실제 서비스에서는 AI가 올린 자료를 읽고 답합니다.</span>')
    st.write("")
    t1, t2, t3, t4, t5, t6 = st.tabs(["요구사항", "아이디어", "학습 계획", "용어·번역", "초안 피드백", "예상 문제"])

    with t1:
        rows = [("과목", e["course"] or "미지정"), ("마감", f"{fmt_date(d)} {e['time']}")]
        for line in (e["details"] or "").split("\n"):
            if ":" in line:
                a, b = line.split(":", 1)
                rows.append((a.strip(), b.strip()))
        H('<div class="cm-cand" style="border-width:1px;border-color:var(--line)"><dl>'
          + "".join(f"<dt>{esc(a)}</dt><dd>{esc(b)}</dd>" for a, b in rows) + "</dl></div>")
        have = {a for a, _ in rows}
        need = [x for x in (["제출", "분량", "주제"] if e["category"] == "과제" else ["범위", "방식"]) if x not in have]
        if need:
            st.warning("아직 확인되지 않은 항목: " + ", ".join(need) + ". 공지를 다시 보거나 교수님께 확인해 두면 좋아요.")
        else:
            st.success("제출에 필요한 정보가 모두 정리돼 있어요.")

    with t2:
        H('<div class="cm-h2">이런 방향은 어때요?</div>')
        for i, idea in enumerate(IDEAS.get(e["course"], GENERIC_IDEAS)):
            st.checkbox(idea, key=f"idea_{e['id']}_{i}")
        st.text_area("떠오르는 생각을 적어 두세요", key=f"memo_{e['id']}", height=100,
                     placeholder="예: 편의점 사례로 하고 싶은데 자료가 충분할지 모르겠음")

    with t3:
        steps = PLAN_STEPS.get(e["category"], PLAN_STEPS["과제"])
        span = max((d - today()).days, 0)
        done = ss.plan_done.setdefault(e["id"], [False] * len(steps))
        H(f'<div class="cm-h2">마감까지 {span}일, {len(steps)}단계로 나눴어요</div>')
        for i, s in enumerate(steps):
            when = today() + timedelta(days=round(i * span / (len(steps) - 1)))
            done[i] = st.checkbox(f"{fmt_date(when)} · {s}", value=done[i], key=f"plan_{e['id']}_{i}")
        st.progress(sum(done) / len(steps), text=f"{sum(done)}/{len(steps)} 단계 완료")

    with t4:
        q = st.text_input("용어 찾기", placeholder="예: 갈등, channel, 尺度")
        shown = [g for g in all_terms if not q.strip() or any(q.strip().lower() in v.lower() for v in g["t"].values())]
        if not shown:
            H('<div class="cm-empty">용어집에 없는 말이에요. 다른 단어로 찾아보세요.</div>')
        for g in shown:
            other = g["t"]["en"] if k == "ko" else g["t"][k]
            body = g["d"][k]
            sub = f'<p style="color:var(--mute)">{esc(g["d"]["ko"])}</p>' if k != "ko" else ""
            H(f'<div class="cm-term"><span class="b">{esc(g["t"]["ko"])}</span><span class="o">{esc(other)}</span>'
              f'<p>{esc(body)}</p>{sub}</div>')
        H('<div class="cm-h2" style="margin-top:18px">강의자료에서 용어 찾아 풀이하기</div>')
        src = st.text_area("강의자료 문장을 붙여 넣어 보세요", height=110, key=f"src_{e['id']}",
                           placeholder="예: 제조업체가 직영 온라인몰을 열면 기존 대리점과 경로 갈등이 발생할 수 있다.")
        if src.strip():
            found = [g for g in [x for v in GLOSSARY.values() for x in v]
                     if any(v.lower() in src.lower() for v in (g["t"]["ko"], g["t"]["en"], g["t"]["ja"], g["t"]["zh"]))]
            if found:
                for g in found:
                    st.markdown(f"**{g['t']['ko']}** ({g['t']['en'] if k == 'ko' else g['t'][k]}): {g['d'][k]}")
            else:
                st.caption("이 문장에서는 용어집에 있는 전공 용어를 찾지 못했어요.")
            st.caption("데모에서는 용어 단위 풀이만 제공해요. 문장 전체 번역은 실제 서비스에서 지원할 예정이에요.")

    with t5:
        draft = st.text_area("초안을 붙여 넣으면 기본 점검을 해 드려요", height=220, key=f"draft_{e['id']}")
        if draft.strip():
            for ok, msg in draft_feedback(draft, [g["t"]["ko"] for g in all_terms]):
                (st.success if ok else st.warning)(msg)
        else:
            H('<p class="cm-note">분량, 문단 구성, 문장 길이, 수업 용어 사용, 출처 표기를 확인해요.</p>')

    with t6:
        rnd = random.Random(e["id"])
        qs = all_terms[:]
        rnd.shuffle(qs)
        qs = qs[:4]
        with st.form(f"quiz_{e['id']}"):
            answers = []
            for i, g in enumerate(qs):
                others = [x["t"]["ko"] for x in all_terms if x is not g]
                rnd.shuffle(others)
                opts = others[:3] + [g["t"]["ko"]]
                rnd.shuffle(opts)
                answers.append(st.radio(f"{i + 1}. {g['d'][k]}", opts, index=None, key=f"q_{e['id']}_{i}"))
            sub = st.form_submit_button("채점하기", type="primary")
        if sub:
            score = sum(1 for a, g in zip(answers, qs) if a == g["t"]["ko"])
            (st.success if score == len(qs) else st.info)(f"{len(qs)}문제 중 {score}문제 맞혔어요.")
            for a, g in zip(answers, qs):
                if a != g["t"]["ko"]:
                    st.caption(f"정답: {g['t']['ko']} · {g['d']['ko']}")


# ─────────────────────────────────────────────────────────────
# 화면: 설정
# ─────────────────────────────────────────────────────────────
def page_settings():
    ss = st.session_state
    p = ss.profile
    H('<h1 class="cm-h1">설정</h1>')
    a, b = st.columns(2, gap="large")
    with a:
        H('<div class="cm-h2">내 정보</div>')
        with st.form("prof"):
            name = st.text_input("이름 또는 닉네임", value=p["name"])
            school = st.selectbox("학교", SCHOOLS, index=SCHOOLS.index(p["school"]) if p["school"] in SCHOOLS else 0)
            major = st.text_input("전공·학과", value=p["major"])
            langs = list(LANGS.keys())
            lang = st.selectbox("용어 해설 언어", langs, index=langs.index(p["lang"]) if p["lang"] in langs else 0)
            if st.form_submit_button("저장", type="primary"):
                p.update(name=name.strip() or p["name"], school=school, major=major.strip(), lang=lang)
                st.toast("내 정보를 저장했어요.")
    with b:
        H('<div class="cm-h2">마감 알림 시점</div>')
        for n in (3, 2, 1, 0):
            ss.stages[n] = st.toggle(f"{STAGES[n][0]} · {STAGES[n][1]}", value=ss.stages.get(n, True), key=f"stg_{n}")
        st.write("")
        H('<div class="cm-h2">외부 캘린더</div>')
        st.download_button("캘린더 파일(.ics) 내려받기", data=ics_text().encode("utf-8"),
                           file_name="campus_mate.ics", mime="text/calendar")
        st.write("")
        H('<div class="cm-h2">데모 초기화</div>')
        st.button("처음부터 다시 시작", on_click=reset_all)
    st.divider()
    H('<p class="cm-note">사진 인식: ' + ('AI 연결됨. 시간표와 공지 캡처를 실제로 읽어요.' if ai_ready() else 'AI 키 없음. 예시 데이터로 동작해요.')
      + ' 대화 이해는 규칙 기반이고 학사일정은 예시 데이터입니다. '
      + ('로그인 중이라 내용이 자동 저장돼요.' if logged_in() and st.session_state.get('store_ok') else '지금은 저장되지 않아서 창을 닫으면 내용이 사라져요.') + '</p>')


# ─────────────────────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────────────────────
NAV = [("대화", ":material/forum:", page_chat),
       ("오늘 할 일", ":material/today:", page_today),
       ("캘린더", ":material/calendar_month:", page_calendar),
       ("시간표", ":material/grid_view:", page_timetable),
       ("과제·시험", ":material/checklist:", page_tasks),
       ("함께 학습", ":material/menu_book:", page_study),
       ("설정", ":material/settings:", page_settings)]


def render():
    ss = st.session_state
    hide = '<style>[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none;}</style>'
    if auth_on() and not logged_in() and not ss.get("guest"):
        H(hide)
        page_login()
        return
    if logged_in():
        load_user()
    if not ss.onboarded:
        H(hide)
        page_onboarding()
        return
    with st.sidebar:
        H('<div class="cm-brand"><div class="cm-logo"></div><div><b>Campus Mate</b><span>말하면 정리되는 캠퍼스 일정</span></div></div>')
        n_alert = len(alerts())
        for name, icon, _ in NAV:
            label = f"{name}  ({n_alert})" if name == "오늘 할 일" and n_alert else name
            st.button(label, key="nav_" + name, icon=icon, width="stretch",
                      type="primary" if ss.page == name else "secondary", on_click=go, args=(name,))
        p = ss.profile
        if logged_in():
            state = "자동 저장 켜짐" if ss.get("store_ok") else "저장 안 됨"
            acct = f'<br>{esc(user_email())}<br>{state}'
        elif auth_on():
            acct = "<br>둘러보기 중 · 저장 안 됨"
        else:
            acct = ""
        H(f'<div class="cm-me"><b>{esc(p["name"])}</b><br>{esc(p["school"])} {esc(p["major"])} {esc(p["grade"])}'
          f'<br>해설 언어: {esc(p["lang"])}{acct}</div>')
        if logged_in():
            st.button("로그아웃", key="logout", icon=":material/logout:", on_click=st.logout, width="stretch")
        elif auth_on():
            st.button("로그인하기", key="to_login", icon=":material/login:", on_click=leave_guest, width="stretch")
    if ss.get("store_msg"):
        st.warning(ss.store_msg)
    dict((n, f) for n, _, f in NAV).get(ss.page, page_chat)()


def main():
    init()
    render()
    save_user()


main()
