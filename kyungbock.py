# -*- coding: utf-8 -*-
"""
경복고등학교 북악제 축제 홈페이지 (Supabase 로그인 연동판)
Streamlit 기반 반응형 웹앱

로그인 방식
    - 학생: 학번+이름 → (최초 1회) 학교이메일로 인증코드(OTP) 발송/확인 → 비밀번호 생성
            → 이후에는 학번+비밀번호로 로그인 (내부적으로 저장된 학교이메일로 인증)
    - 교직원: 인증코드 → (최초 1회) 코드에 사전 등록된 이름 확인 + 아이디/비밀번호 생성
            → 이후에는 아이디+비밀번호로 로그인
            (교직원은 실제 이메일이 없으므로 "아이디 + 가짜 이메일"로 Supabase Auth 계정을 만듭니다)

사전 준비 (필수)
    1) Supabase 프로젝트 SQL Editor에서 supabase_setup.sql 실행
    2) Supabase 대시보드 > Authentication > Providers > Email 에서
       "Confirm email"(이메일 인증) 을 반드시 OFF 로 설정
       (교직원 가짜 이메일은 인증 메일을 받을 수 없기 때문입니다)
    3) Supabase 대시보드 > Authentication > Email Templates > Magic Link
       템플릿 본문에 {{ .Token }} 을 추가해야 학생에게 6자리 인증코드가 발송됩니다
       (기본 템플릿은 클릭형 링크만 있습니다)
    4) .streamlit/secrets.toml 에 아래 값 채우기
        SUPABASE_URL = "https://xxxx.supabase.co"
        SUPABASE_ANON_KEY = "..."
        SUPABASE_SERVICE_KEY = "..."   # 관리자 기능(권한부여, 인증코드 발급 등)에 필요, 선택
        COOKIE_PASSWORD = "아무 긴 임의 문자열"  # 로그인 유지용 쿠키 암호화 키 (필수 권장)

실행:
    pip install streamlit supabase streamlit-cookies-manager
    streamlit run app.py


[추가 기능 - 공지 공개범위 / FAQ / 랜덤 / 부스 분류]
공지사항은 전체 공개 또는 학생/교직원 전용으로 설정할 수 있습니다. FAQ는 Supabase에서 관리하며
관리자는 추가/수정/삭제할 수 있습니다. 부스는 동아리 부스/먹거리 부스로 분류하고 랜덤 추천 기능을 제공합니다.
방문자 통계 및 방문 기록 기능은 제거했습니다.

----------------------------------------------------------------------
[수정 사항 3 - 관리자가 공지사항을 수정/삭제하지 못하던 문제 해결]
기존 코드의 "사이트 관리" 탭에는 공지사항을 새로 "등록"하는 폼만 있고,
이미 등록된 공지사항을 수정하거나 삭제하는 기능은 아예 없었습니다.

해결: page_admin() 의 "사이트 관리" 탭에 "공지사항 관리" 섹션을 추가했습니다.
----------------------------------------------------------------------

[수정 사항 4 - 공지사항 / 부스 정보가 메인 화면에 반영되지 않던 문제 해결]
공지사항(notices)과 부스(booths)를 Supabase 테이블로 옮기고, 페이지를 그릴 때마다
fetch_notices() / fetch_booths() 로 DB에서 직접 읽어오도록 바꿨습니다.

DB 준비: 아래 SQL을 Supabase SQL Editor에서 한 번 실행해주세요.

    create table if not exists notices (
        id uuid primary key default gen_random_uuid(),
        title text not null,
        content text,
        is_new boolean not null default true,
        created_at timestamptz not null default now()
    );
    alter table notices enable row level security;
    create policy "notices are viewable by everyone"
        on notices for select
        using (true);

    create table if not exists booths (
        id uuid primary key default gen_random_uuid(),
        name text not null,
        category text,
        place text,
        hours text,
        description text,
        icon text,
        image text,
        created_at timestamptz not null default now()
    );
    alter table booths enable row level security;
    create policy "booths are viewable by everyone"
        on booths for select
        using (true);
----------------------------------------------------------------------

[수정 사항 5 - 사이드바(드로어)에서 '메인' 항목 제거 + 헤더 클릭 시 메인 이동]
드로어 메뉴에서는 '메인' 항목을 뺐습니다. 로고 클릭으로 메인 이동이 가능합니다.
----------------------------------------------------------------------

[수정 사항 6 - 교직원 로그인 방식 변경: 코드에 사전 등록된 이름 + 아이디/비밀번호]
관리자가 인증코드를 발급할 때 담당 선생님 "이름"도 함께 입력합니다(staff_codes.name).
선생님은 최초 등록 시 코드 확인 후 "아이디(로그인 ID)"와 "비밀번호"를 새로 만듭니다.
이후 로그인은 "아이디+비밀번호"로 합니다.

DB 준비 (추가 SQL):
    alter table staff_codes add column if not exists name text;
    alter table profiles add column if not exists staff_username text unique;
----------------------------------------------------------------------

[수정 사항 7 - 부스 사진 + 아이콘 함께 표시]
사진이 있어도 아이콘이 사진 위 모서리에 작은 배지 형태로 함께 보이도록 했습니다.
----------------------------------------------------------------------

[수정 사항 8 - 공지사항/부스 목록 캐싱으로 체감 속도 개선 + DB 요청 절감]
fetch_notices()/fetch_booths()에 @st.cache_data(ttl=...)를 적용했습니다.
----------------------------------------------------------------------

[수정 사항 9 - (제거됨) 방명록 기능]
이전 버전에는 방명록(guestbook) 페이지가 있었으나, 요청에 따라 완전히 제거했습니다.
(테이블/함수/메뉴 항목을 모두 삭제했습니다. 기존에 guestbook 테이블을 만들어두셨다면
 더 이상 이 앱에서 사용하지 않으니 필요 없다면 Supabase에서 직접 삭제하셔도 됩니다.)
----------------------------------------------------------------------

[수정 사항 10 - 관리자 방문자 통계]
방문자가 사이트에 처음 접속(세션당 1회)하면 조용히 방문 기록을 1건 남기고, 관리자
페이지에서 누적 방문자 수와 최근 14일 일별 방문자 추이를 확인할 수 있습니다.
개인을 특정할 수 있는 정보(IP, 쿠키 등)는 저장하지 않고 방문 시각만 기록합니다.

DB 준비 (Supabase SQL Editor에서 한 번 실행):

    create table if not exists visits (
        id uuid primary key default gen_random_uuid(),
        created_at timestamptz not null default now()
    );
    alter table visits enable row level security;
    create policy "visits are insertable by everyone"
        on visits for insert with check (true);
    create policy "visits are viewable by everyone"
        on visits for select using (true);
----------------------------------------------------------------------

[수정 사항 11 - 프로그램/시간표를 관리자가 추가·수정·삭제 가능하도록 변경]
기존에는 프로그램(programs)과 시간표(schedule)가 st.session_state에만 저장되는
데모용 인메모리 데이터였습니다. 그래서 관리자가 수정할 방법이 없었고, 서버가
재시작되면 초기화되었습니다.

해결:
    1) 프로그램(programs)과 시간표(schedule)를 각각 Supabase 테이블로 옮기고,
       fetch_programs() / fetch_schedule_by_day() 로 항상 DB에서 최신 데이터를
       읽어오도록 했습니다.
    2) "프로그램" 페이지, "시간표" 페이지 모두 공지사항/부스 정보 페이지와
       동일한 패턴으로 — 각 항목 아래에 관리자 전용 "수정/삭제" 폼을 열 수 있게
       하고, 화면 우측 하단 "+" 버튼으로 새 항목을 등록하는 전용 페이지
       (프로그램 등록 / 시간표 등록)로 이동하도록 만들었습니다.
    3) 요청하신 대로 "프로그램 구성" 메뉴를 새로 만들되, **사이드바(햄버거 메뉴)
       에만** 노출됩니다(메인 화면 상단 아이콘 메뉴에는 넣지 않았습니다). 이 메뉴는
       기존 "프로그램" 페이지로 그대로 연결되며, 그 페이지 안에서 관리자는 등록·
       수정·삭제를, 일반 방문자는 조회를 할 수 있습니다.

DB 준비 (Supabase SQL Editor에서 한 번 실행):

    create table if not exists programs (
        id uuid primary key default gen_random_uuid(),
        name text not null,
        category text,
        program_date text,
        program_time text,
        place text,
        description text,
        icon text,
        created_at timestamptz not null default now()
    );
    alter table programs enable row level security;
    create policy "programs are viewable by everyone"
        on programs for select using (true);

    create table if not exists schedule (
        id uuid primary key default gen_random_uuid(),
        day text not null,
        time text not null,
        program text not null,
        place text,
        created_at timestamptz not null default now()
    );
    alter table schedule enable row level security;
    create policy "schedule is viewable by everyone"
        on schedule for select using (true);

    (등록/수정/삭제는 SUPABASE_SERVICE_KEY로 RLS를 우회해 처리하므로
     별도의 insert/update/delete 정책은 필요 없습니다.)
----------------------------------------------------------------------
"""

import streamlit as st
import streamlit.components.v1 as components
import folium
import base64
import random
import io
from datetime import datetime, date, time as dtime, timedelta
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

# ----------------------------------------------------------------------
# 학교 로고 (경복고등학교 엠블럼)
# 제공된 투명 로고를 SVG 벡터 형태로 사용합니다. 흰색 배경을 넣지 않습니다.
LOGO_PNG_BASE64 = "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"
LOGO_SVG_DATA_URI = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0NjYgNDY1IiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0Ij48cGF0aCBkPSJNIDIzNSwyMzQgMjM1LDMyNyAyMzYsMzI4IDMzNCwzMjggMzM0LDIzNCBaIE0gMjM1LDE2MyAyMzUsMjIzIDMzNCwyMjMgMzM0LDE2MiAyMzYsMTYyIFogTSAxMzMsMTYyIDEzMiwxNjMgMTMyLDE4NyAxNjYsMTg3IDE2NywxODggMTY3LDMyOCAxOTIsMzI4IDE5MiwxODggMTkzLDE4NyAyMjYsMTg3IDIyNiwxNjIgWiBNIDIwMSwxOTYgMjAxLDMyOCAyMjYsMzI4IDIyNiwxOTYgWiBNIDEzMiwxOTYgMTMyLDMyOCAxNTcsMzI4IDE1NywxOTYgWiBNIDIzNSwxMjggMjM1LDE1MyAzMzQsMTUzIDMzNCwxMjggWiBNIDEzMiwxMjggMTMyLDE1MyAyMjYsMTUzIDIyNiwxMjggWiBNIDM2MiwzODMgMzYwLDM4MyAzNTgsMzg1IDM1NywzODUgMzU1LDM4NyAzNTQsMzg3IDM1MywzODggMzUyLDM4NyAzNTIsMzg2IDM1MSwzODUgMzQ5LDM4NSAzNDgsMzg2IDM0NywzODYgMzQ2LDM4NyAzNDYsMzg5IDM0OCwzOTEgMzQ1LDM5NCAzNDQsMzk0IDM0MiwzOTYgMzQxLDM5NiAzNDEsMzk5IDM0MCw0MDAgMzM4LDQwMCAzMzYsMzk4IDMzNiwzOTcgMzM1LDM5NiAzMzMsMzk2IDMzMiwzOTcgMzMxLDM5NyAzMzAsMzk4IDMzMCwzOTkgMzMzLDQwMiAzMzMsNDA0IDMzMSw0MDYgMzMxLDQwNyAzMzMsNDA5IDMzMyw0MTAgMzM0LDQxMCAzMzUsNDA5IDMzNyw0MDkgMzM4LDQxMCAzMzgsNDEyIDMzOSw0MTMgMzM5LDQxNiAzNDAsNDE3IDM0MCw0MjQgMzQxLDQyNCAzNDIsNDI1IDM0NSw0MjUgMzQ1LDQyMiAzNDYsNDIxIDM0Nyw0MjIgMzQ3LDQyMyAzNTAsNDI2IDM1MCw0MjcgMzUyLDQyOSAzNTIsNDMwIDM1NCw0MzIgMzU2LDQzMiAzNTgsNDMwIDM1OCw0MjkgMzU3LDQyOCAzNTcsNDI3IDM1Niw0MjYgMzU3LDQyNSAzNTgsNDI1IDM1OSw0MjYgMzYwLDQyNiAzNjEsNDI3IDM2Miw0MjcgMzYzLDQyNiAzNjMsNDI1IDM2NCw0MjQgMzY0LDQyMyAzNjUsNDIyIDM2NSw0MjAgMzY2LDQxOSAzNjYsNDE4IDM2Nyw0MTcgMzY3LDQxNSAzNjgsNDE0IDM4MSw0MTQgMzgxLDQwOCAzNzYsNDA4IDM3NSw0MDkgMzY5LDQwOSAzNjgsNDA4IDM2OCw0MDMgMzY3LDQwMiAzNjcsMzk5IDM2NiwzOTggMzY4LDM5NiAzNjgsMzkyIDM2NywzOTEgMzY0LDM5MSAzNjMsMzkyIDM1OSwzOTIgMzU4LDM5MSAzNjEsMzg4IDM2MiwzODggMzYzLDM4NyAzNjMsMzg0IFogTSAzNTAsMjQyIDM1MCwyNTkgNDE1LDI1OSA0MTUsMjU3IDQxNiwyNTYgNDE2LDI0OCA0MTcsMjQ3IDQxNywyNDIgWiBNIDUwLDI0MiA1MCwyNTMgNTEsMjU0IDUxLDI1OSAxMTYsMjU5IDExNiwyNDIgWiBNIDMxOCw0MDYgMzE3LDQwNiAzMTYsNDA3IDMxNCw0MDcgMzEzLDQwOCAzMTEsNDA4IDMxMCw0MDkgMzA5LDQwOSAzMDksNDEwIDMwOCw0MTEgMzA0LDQxMSAzMDIsNDEzIDMwMSw0MTIgMjk5LDQxMiAyOTksNDEzIDI5OCw0MTQgMjk4LDQxNSAyOTcsNDE2IDI5NSw0MTQgMjk0LDQxNCAyOTMsNDE1IDI5Miw0MTUgMjkxLDQxNiAyOTAsNDE2IDI4OSw0MTcgMjg4LDQxNyAyODcsNDE4IDI4Niw0MTggMjg2LDQxOSAyODcsNDIwIDI4Nyw0MjEgMjg4LDQyMiAyODgsNDIzIDI4OSw0MjQgMjg5LDQyNiAyOTAsNDI3IDI5MCw0MjggMjkxLDQyOSAyOTEsNDMwIDI5Miw0MzEgMjkyLDQzMiAyOTAsNDM0IDI5MCw0MzYgMjkxLDQzNyAyOTEsNDQwIDI5Miw0NDEgMjkyLDQ0MiAyOTMsNDQyIDI5NCw0NDEgMjk2LDQ0MSAyOTcsNDQwIDI5Nyw0MzggMjk2LDQzNyAyOTgsNDM1IDI5OSw0MzUgMzAwLDQzNiAzMDAsNDM3IDMwMSw0MzggMzAxLDQ0MCAzMDIsNDQwIDMwMyw0MzkgMzA0LDQzOSAzMDUsNDM4IDMwNyw0MzggMzA4LDQzNyAzMTAsNDM3IDMxMSw0MzggMzA4LDQ0MSAzMDcsNDQxIDMwNiw0NDIgMzA0LDQ0MiAzMDMsNDQzIDMwMSw0NDMgMzAwLDQ0NCAyOTgsNDQ0IDI5Nyw0NDUgMjk2LDQ0NSAyOTYsNDQ5IDI5OCw0NDkgMjk5LDQ0OCAzMDEsNDQ4IDMwMiw0NDcgMzA0LDQ0NyAzMDUsNDQ2IDMwNiw0NDYgMzA3LDQ0NSAzMDksNDQ1IDMxMCw0NDQgMzExLDQ0NCAzMTIsNDQ1IDMxMiw0NDYgMzEwLDQ0OCAzMDksNDQ4IDMwOSw0NTAgMzExLDQ1MiAzMTQsNDUyIDMxNSw0NTEgMzE2LDQ1MSAzMTgsNDQ5IDMxOCw0NDggMzE5LDQ0NyAzMTksNDQ2IDMxOCw0NDUgMzE4LDQ0MyAzMTcsNDQyIDMxOCw0NDEgMzE5LDQ0MSAzMjAsNDQwIDMyMiw0NDAgMzIzLDQzOSAzMjUsNDM5IDMyNiw0MzggMzI3LDQzOCAzMjgsNDM3IDMzMCw0MzcgMzMxLDQzNiAzMzEsNDMzIDMyNyw0MzMgMzI2LDQzNCAzMjUsNDM0IDMyNCw0MzUgMzIyLDQzNSAzMjEsNDM2IDMyMCw0MzYgMzE5LDQzNyAzMTgsNDM3IDMxNyw0MzYgMzE4LDQzNSAzMTgsNDM0IDMxOSw0MzMgMzE5LDQzMiAzMjAsNDMxIDMyMCw0MjkgMzE5LDQyOSAzMTgsNDI4IDMxOSw0MjcgMzIwLDQyNyAzMjEsNDI2IDMyMiw0MjYgMzIzLDQyNyAzMjMsNDI4IDMyNCw0MjkgMzI3LDQyOSAzMjgsNDI4IDMyOSw0MjggMzI5LDQyNyAzMjgsNDI2IDMyOCw0MjQgMzI3LDQyMyAzMjcsNDIxIDMyNiw0MjAgMzI1LDQyMCAzMjQsNDIxIDMyMyw0MjEgMzIyLDQyMCAzMjIsNDE4IDMyMSw0MTcgMzIxLDQxNSAzMjAsNDE0IDMyMCw0MTIgMzE5LDQxMSAzMTksNDA4IDMxOCw0MDcgWiBNIDExNCwzODUgMTEyLDM4NyAxMTIsMzg4IDExMCwzOTAgMTEwLDM5MSAxMDgsMzkzIDEwOCwzOTQgMTA3LDM5NSAxMDcsMzk3IDEwNiwzOTggMTA1LDM5OCAxMDMsMzk2IDEwMiwzOTYgMTAxLDM5NSA5OSwzOTUgOTksMzk2IDk4LDM5NyA5OCwzOTggOTksMzk4IDEwMSw0MDAgMTAyLDQwMCAxMDQsNDAyIDEwMyw0MDMgMTAwLDQwMyAxMDAsNDA0IDk3LDQwNyA5Nyw0MDggOTYsNDA5IDk2LDQxMCA5Nyw0MTEgOTYsNDEyIDk1LDQxMiA5NCw0MTEgOTAsNDExIDg5LDQxMCA4OCw0MTAgODgsNDEyIDg3LDQxMyA4Nyw0MTUgODgsNDE1IDg5LDQxNiAxMDAsNDE2IDEwMCw0MTQgMTAxLDQxMyAxMDQsNDE2IDEwNCw0MTcgMTAyLDQxOSAxMDEsNDE5IDEwMCw0MTggOTksNDE4IDk5LDQyMCA5OCw0MjEgOTgsNDIzIDk5LDQyMyAxMDAsNDI0IDEwMSw0MjQgMTAyLDQyNSAxMDUsNDI1IDEwOCw0MjIgMTA4LDQyMSAxMDksNDIwIDExMSw0MjAgMTEyLDQyMSAxMTEsNDIyIDExMSw0MjYgMTEyLDQyNyAxMTIsNDI5IDExMyw0MzAgMTEzLDQzMSAxMTQsNDMyIDExNCw0MzMgMTE1LDQzNCAxMTcsNDM0IDExOCw0MzMgMTIwLDQzMyAxMjAsNDMyIDExOCw0MzAgMTE4LDQyOSAxMTYsNDI3IDExNiw0MjYgMTE3LDQyNSAxMTksNDI1IDExOSw0MjQgMTIyLDQyMSAxMjIsNDIwIDEyMyw0MTkgMTIzLDQxNyAxMjQsNDE2IDEyNSw0MTYgMTI4LDQxOSAxMjksNDE5IDEzMSw0MTcgMTMxLDQxNSAxMzAsNDE1IDEyOCw0MTMgMTI3LDQxMyAxMjUsNDExIDEyNiw0MTAgMTI4LDQxMCAxMjksNDA5IDEyOSw0MDggMTMxLDQwNiAxMzEsNDA1IDEzMyw0MDMgMTMzLDQwMiAxMzUsNDAwIDEzNSwzOTkgMTM0LDM5OCAxMzMsMzk4IDEzMSwzOTYgMTMwLDM5NiAxMjgsMzk0IDEyNywzOTQgMTI1LDM5MiAxMjQsMzkyIDEyMiwzOTAgMTIxLDM5MCAxMTksMzg4IDExOCwzODggMTE1LDM4NSBaIE0gMjQzLDQyMyAyNDIsNDI0IDI0Miw0MjYgMjQxLDQyNyAyNDEsNDI4IDI0MCw0MjkgMjQwLDQzMCAyMzgsNDMyIDIzOCw0MzMgMjQwLDQzNSAyNDIsNDM1IDI0NCw0MzMgMjQ0LDQzMiAyNDUsNDMxIDI0Nyw0MzEgMjQ4LDQzMiAyNDgsNDMzIDI0OSw0MzQgMjUzLDQzNCAyNTQsNDMzIDI1NSw0MzQgMjU1LDQzNiAyNTQsNDM3IDI0OCw0MzcgMjQ3LDQzOCAyNDQsNDM4IDI0NCw0NDAgMjQ1LDQ0MSAyNDUsNDQyIDI0OCw0NDIgMjQ5LDQ0MSAyNTUsNDQxIDI1Niw0NDIgMjU0LDQ0NCAyNDYsNDQ0IDI0NSw0NDUgMjQxLDQ0NSAyNDEsNDQ5IDI0OCw0NDkgMjQ5LDQ0OCAyNTUsNDQ4IDI1Niw0NDcgMjYzLDQ0NyAyNjQsNDQ2IDI2Nyw0NDYgMjY4LDQ0NyAyNjgsNDQ4IDI2Nyw0NDkgMjYyLDQ0OSAyNjEsNDUwIDI1NCw0NTAgMjUzLDQ1MSAyNDUsNDUxIDI0NCw0NTIgMjQ0LDQ1NiAyNDgsNDU2IDI0OSw0NTcgMjQ5LDQ1OCAyNTMsNDYyIDI1Myw0NjMgMjU2LDQ2MyAyNTgsNDYxIDI1OCw0NjAgMjU0LDQ1NiAyNTUsNDU1IDI1Niw0NTUgMjU3LDQ1NCAyNjUsNDU0IDI2Niw0NTMgMjY4LDQ1MyAyNjksNDU0IDI2OSw0NTYgMjY3LDQ1OCAyNjUsNDU4IDI2NSw0NjAgMjY2LDQ2MSAyNjYsNDYyIDI2Nyw0NjMgMjcxLDQ2MyAyNzQsNDYwIDI3NCw0NTkgMjc1LDQ1OCAyNzUsNDU1IDI3NCw0NTQgMjc1LDQ1MyAyNzYsNDUzIDI3Nyw0NTIgMjc5LDQ1MiAyNzksNDQ4IDI3NCw0NDggMjczLDQ0NyAyNzMsNDQ2IDI3NCw0NDUgMjc5LDQ0NSAyNzksNDQxIDI3MSw0NDEgMjcwLDQ0MiAyNjMsNDQyIDI2Miw0NDEgMjYzLDQ0MCAyNjQsNDQwIDI2NSw0MzkgMjcxLDQzOSAyNzIsNDM4IDI3NCw0MzggMjc0LDQzNSAyNjYsNDM1IDI2NSw0MzYgMjYzLDQzNiAyNjIsNDM1IDI2Miw0MzMgMjY0LDQzMSAyNjQsNDMwIDI2Niw0MjggMjY4LDQyOCAyNjksNDI5IDI2OSw0MzIgMjcxLDQzMiAyNzIsNDMxIDI3NCw0MzEgMjc0LDQyOCAyNzUsNDI3IDI3Niw0MjcgMjc3LDQyNiAyNzcsNDIzIDI3Miw0MjMgMjcxLDQyNCAyNjcsNDI0IDI2Niw0MjMgMjY2LDQyMiAyNjEsNDIyIDI2MSw0MjUgMjYwLDQyNiAyNjAsNDI3IDI1OSw0MjggMjU5LDQyOSAyNTgsNDMwIDI1Nyw0MjkgMjU3LDQyNiAyNDgsNDI2IDI0Nyw0MjUgMjQ3LDQyNCAyNDUsNDI0IDI0NCw0MjMgWiBNIDE0NCw0MTQgMTQzLDQxNSAxNDMsNDE2IDE0Miw0MTcgMTQyLDQxOCAxNDMsNDE5IDE0NSw0MTkgMTQ2LDQyMCAxNDcsNDIwIDE0OCw0MjEgMTQ4LDQyMiAxNDcsNDIzIDE0Nyw0MjQgMTQ2LDQyNSAxNDUsNDI0IDE0NSw0MjIgMTQ0LDQyMiAxNDMsNDIxIDE0Miw0MjEgMTQyLDQyMiAxNDEsNDIzIDE0MSw0MjQgMTQwLDQyNSAxNDAsNDI3IDEzOSw0MjggMTM5LDQyOSAxMzgsNDMwIDEzOCw0MzEgMTM3LDQzMiAxMzcsNDMzIDEzNiw0MzQgMTM2LDQzNSAxMzQsNDM3IDEzNCw0MzkgMTM1LDQzOSAxMzYsNDQwIDEzOCw0NDAgMTM4LDQzOSAxNDAsNDM3IDE0MCw0MzYgMTQxLDQzNSAxNDIsNDM2IDE0Miw0MzggMTQxLDQzOSAxNDEsNDQwIDE0MCw0NDEgMTQwLDQ0MyAxMzksNDQ0IDEzOSw0NDYgMTQwLDQ0NyAxNDMsNDQ3IDE0NCw0NDYgMTQ0LDQ0NCAxNDUsNDQzIDE0NSw0NDEgMTQ2LDQ0MCAxNDcsNDQxIDE0OCw0NDEgMTQ5LDQ0MiAxNTEsNDQyIDE1MSw0NDEgMTUyLDQ0MCAxNTIsNDM5IDE1Myw0MzggMTU0LDQzOSAxNTQsNDQxIDE1Myw0NDIgMTUzLDQ0MyAxNTIsNDQ0IDE1Miw0NDYgMTUxLDQ0NyAxNTEsNDUwIDE1Miw0NTEgMTU0LDQ1MSAxNTUsNDUyIDE1Nyw0NTIgMTU4LDQ1MyAxNjAsNDUzIDE2MSw0NTQgMTYzLDQ1NCAxNjQsNDU1IDE2Niw0NTUgMTY3LDQ1NiAxNjgsNDU2IDE2OSw0NTcgMTcxLDQ1NyAxNzEsNDU2IDE3Miw0NTUgMTcyLDQ1MyAxNzMsNDUyIDE3Myw0NTEgMTc0LDQ1MCAxNzQsNDQ4IDE3NSw0NDcgMTc1LDQ0NSAxNzYsNDQ0IDE3Niw0NDMgMTc3LDQ0MiAxNzcsNDM5IDE3Niw0MzkgMTc1LDQzOCAxNzMsNDM4IDE3Miw0MzcgMTcxLDQzNyAxNzAsNDM2IDE2OCw0MzYgMTY3LDQzNSAxNjUsNDM1IDE2NCw0MzQgMTYzLDQzNCAxNjIsNDMzIDE2MCw0MzMgMTU5LDQzMiAxNTcsNDMyIDE1Niw0MzMgMTU1LDQzMiAxNTUsNDMxIDE1Niw0MzAgMTU2LDQyNyAxNTUsNDI2IDE1Myw0MjYgMTUzLDQyNyAxNTIsNDI4IDE1MSw0MjcgMTUxLDQyNSAxNTIsNDI0IDE1Miw0MjMgMTUzLDQyMiAxNTQsNDIyIDE1NSw0MjMgMTU2LDQyMyAxNTcsNDI0IDE1OSw0MjQgMTU5LDQyMiAxNjAsNDIxIDE2MCw0MjAgMTU5LDQxOSAxNTcsNDE5IDE1Niw0MTggMTU0LDQxOCAxNTMsNDE3IDE1Miw0MTcgMTUxLDQxNiAxNDksNDE2IDE0OCw0MTUgMTQ2LDQxNSAxNDUsNDE0IFogTSAxMjYsMjYgMTI1LDI3IDEyNCwyNyAxMjMsMjggMTIyLDI4IDEyMCwzMCAxMjAsMzEgMTE5LDMyIDExOSwzMyAxMTgsMzQgMTE4LDQyIDExOSw0MyAxMTksNDQgMTIwLDQ1IDEyMCw0NiAxMjEsNDcgMTIxLDQ4IDEyMiw0OSAxMjIsNTAgMTI0LDUyIDEyNCw1MyAxMjYsNTUgMTI3LDU1IDEyOCw1NiAxMjksNTYgMTMwLDU3IDEzMiw1NyAxMzMsNTggMTM1LDU4IDEzNiw1NyAxMzgsNTcgMTM5LDU2IDE0MCw1NiAxNDEsNTUgMTQyLDU1IDE0NCw1MyAxNDQsNTIgMTQ1LDUxIDE0NSw0OSAxNDYsNDggMTQ2LDQ0IDE0NSw0MyAxNDUsNDAgMTQ0LDM5IDE0NCwzOCAxNDMsMzcgMTQzLDM2IDE0MiwzNSAxNDIsMzQgMTQxLDMzIDE0MSwzMiAxMzcsMjggMTM2LDI4IDEzNSwyNyAxMzQsMjcgMTMzLDI2IFogTSA0NTQsMTU5IDQ1MywxNTkgNDUyLDE1OCA0NDgsMTU4IDQ0NywxNTcgNDQ1LDE1NyA0NDQsMTU4IDQzOSwxNTggNDM4LDE1OSA0MzYsMTU5IDQzNSwxNjAgNDM0LDE2MCA0MzIsMTYyIDQzMSwxNjIgNDI4LDE2NSA0MjgsMTY2IDQyNywxNjcgNDI3LDE2OSA0MjYsMTcwIDQyNiwxNzMgNDI3LDE3NCA0MjcsMTc2IDQyOCwxNzcgNDI4LDE3OCA0MzIsMTgyIDQzMywxODIgNDM0LDE4MyA0NDQsMTgzIDQ0NSwxODIgNDQ4LDE4MiA0NDksMTgxIDQ1MCwxODEgNDUxLDE4MCA0NTIsMTgwIDQ1NCwxNzggNDU1LDE3OCA0NTYsMTc3IDQ1NiwxNzYgNDU4LDE3NCA0NTgsMTczIDQ1OSwxNzIgNDU5LDE2NiA0NTgsMTY1IDQ1OCwxNjQgNDU3LDE2MyA0NTcsMTYyIFogTSA0NDEsMTI1IDQ0MCwxMjUgNDM5LDEyNCA0MzgsMTI0IDQzNywxMjMgNDMwLDEyMyA0MjksMTI0IDQyNiwxMjQgNDI1LDEyNSA0MjQsMTI1IDQyMywxMjYgNDIyLDEyNiA0MjAsMTI4IDQxOSwxMjggNDE1LDEzMiA0MTUsMTMzIDQxNCwxMzQgNDE0LDEzNSA0MTMsMTM2IDQxMywxNDEgNDE0LDE0MiA0MTQsMTQzIDQxNSwxNDQgNDE1LDE0NSA0MTksMTQ5IDQyMCwxNDkgNDIxLDE1MCA0MzAsMTUwIDQzMSwxNDkgNDMzLDE0OSA0MzQsMTQ4IDQzNSwxNDggNDM3LDE0NiA0MzgsMTQ2IDQ0NCwxNDAgNDQ0LDEzOSA0NDUsMTM4IDQ0NSwxMzEgNDQ0LDEzMCA0NDQsMTI5IDQ0MywxMjggNDQzLDEyNyBaIE0gMzUwLDIxNiAzNTAsMjI1IDQxNywyMjUgNDE3LDIyMiA0MTYsMjIxIDQxNiwyMTYgWiBNIDUwLDIxNiA1MCwyMjUgMTE2LDIyNSAxMTYsMjE2IFogTSAyNjEsMTg4IDI2MiwxODcgMzA3LDE4NyAzMDgsMTg4IDMwOCwxOTggMzA3LDE5OSAyNjIsMTk5IDI2MSwxOTggWiBNIDIxNiwzNjQgMjE1LDM2NSAyMTQsMzY1IDIxMywzNjYgMjEyLDM2NiAyMTAsMzY4IDIxMCwzNjkgMjA5LDM3MCAyMDksMzc0IDIwOCwzNzUgMjA4LDM3NiAyMDksMzc3IDIwOSwzODAgMjEwLDM4MSAyMTAsMzgyIDIxMywzODUgMjE2LDM4NSAyMTcsMzg2IDIyMCwzODYgMjIxLDM4NSAyMjIsMzg1IDIyMywzODQgMjI0LDM4NSAyMjQsMzg3IDIyMywzODggMjIzLDM4OSAyMjAsMzkyIDIxNywzOTIgMjE2LDM5MyAyMTUsMzkzIDIxNCwzOTIgMjExLDM5MiAyMTEsMzkzIDIxMCwzOTQgMjEwLDM5NyAyMTIsMzk3IDIxMywzOTggMjIwLDM5OCAyMjEsMzk3IDIyMywzOTcgMjI3LDM5MyAyMjcsMzkyIDIyOCwzOTEgMjI4LDM5MCAyMjksMzg5IDIyOSwzODYgMjMwLDM4NSAyMzAsMzc0IDIyOSwzNzMgMjI5LDM3MSAyMjgsMzcwIDIyOCwzNjkgMjI3LDM2OCAyMjcsMzY3IDIyNiwzNjYgMjI1LDM2NiAyMjQsMzY1IDIyMywzNjUgMjIyLDM2NCBaIE0gOTksNDQgOTgsNDUgOTYsNDUgOTMsNDggOTIsNDggOTAsNTAgODksNTAgODgsNTEgODgsNTIgOTAsNTQgOTAsNTUgOTMsNTggOTMsNTkgOTYsNjIgOTYsNjMgOTksNjYgOTksNjcgMTAxLDY5IDEwMSw3MCAxMDQsNzMgMTA0LDc0IDEwNiw3NiAxMDgsNzYgMTA5LDc1IDExMCw3NSAxMTIsNzMgMTEzLDczIDExNiw3MCAxMTYsNjkgMTE3LDY4IDExNyw2NyAxMTgsNjYgMTE4LDYzIDExNyw2MiAxMTcsNjEgMTE2LDYwIDExNiw1OSAxMTQsNTcgMTEzLDU3IDExMiw1NiAxMDgsNTYgMTA3LDU1IDEwOCw1NCAxMDgsNTIgMTA3LDUxIDEwNyw0OSAxMDUsNDcgMTA1LDQ2IDEwNCw0NiAxMDIsNDQgWiBNIDUwLDMwMyA0OSwzMDIgNDgsMzAyIDQ3LDMwMyA0NiwzMDMgNDUsMzA0IDQ0LDMwNCA0MCwzMDggNDAsMzEwIDM5LDMxMSAzOSwzMTIgMzgsMzEzIDM4LDMxNSAzNywzMTYgMzcsMzIwIDM2LDMyMSAzMywzMTggMzIsMzE4IDMxLDMxNyAzMCwzMTcgMjksMzE2IDI3LDMxNiAyNiwzMTUgMTksMzE1IDE4LDMxNiAxNSwzMTYgMTUsMzE5IDE2LDMyMCAxNiwzMjEgMjEsMzI2IDIyLDMyNiAyMywzMjcgMjQsMzI3IDI1LDMyOCAyOCwzMjggMjksMzI5IDMyLDMyOSAzMywzMjggMzcsMzI4IDM4LDMyNyA0MCwzMjcgNDEsMzI2IDQyLDMyNiA0OCwzMjAgNDgsMzE5IDQ5LDMxOCA0OSwzMTcgNTAsMzE2IDUwLDMxMyA1MSwzMTIgNTEsMzA3IDUwLDMwNiBaIE0gNzEsMzQzIDcwLDM0MiA2OSwzNDIgNjYsMzQ1IDY2LDM0NiA2NCwzNDggNjQsMzQ5IDYzLDM1MCA2MywzNTIgNjIsMzUzIDYyLDM2MSA2MywzNjIgNjMsMzYzIDYyLDM2NCA2MSwzNjQgNjAsMzYzIDU5LDM2MyA1OCwzNjIgNTYsMzYyIDU1LDM2MSA0NSwzNjEgNDQsMzYyIDQzLDM2MiA0MiwzNjMgNDEsMzYzIDQwLDM2NCA0MCwzNjYgNDMsMzY5IDQ0LDM2OSA0NiwzNzEgNDgsMzcxIDQ5LDM3MiA1MiwzNzIgNTMsMzczIDU3LDM3MyA1OCwzNzIgNjEsMzcyIDYyLDM3MSA2MywzNzEgNjQsMzcwIDY1LDM3MCA2NiwzNjkgNjcsMzY5IDcwLDM2NiA3MCwzNjUgNzIsMzYzIDcyLDM2MiA3MywzNjEgNzMsMzU5IDc0LDM1OCA3NCwzNDkgNzMsMzQ4IDczLDM0NyA3MiwzNDYgNzIsMzQ1IDcxLDM0NCBaIE0gNDE3LDMwMyA0MTcsMzA2IDQxNiwzMDcgNDE2LDMxMiA0MTcsMzEzIDQxNywzMTYgNDE4LDMxNyA0MTgsMzE4IDQxOSwzMTkgNDE5LDMyMCA0MjUsMzI2IDQyNiwzMjYgNDI3LDMyNyA0MjksMzI3IDQzMCwzMjggNDM0LDMyOCA0MzUsMzI5IDQzOCwzMjkgNDM5LDMyOCA0NDIsMzI4IDQ0MywzMjcgNDQ0LDMyNyA0NDUsMzI2IDQ0NiwzMjYgNDUxLDMyMSA0NTEsMzIwIDQ1MiwzMTkgNDUyLDMxNiA0NDksMzE2IDQ0OCwzMTUgNDQxLDMxNSA0NDAsMzE2IDQzOCwzMTYgNDM3LDMxNyA0MzYsMzE3IDQzNCwzMTkgNDMzLDMxOSA0MzEsMzIxIDQzMCwzMjAgNDMwLDMxNiA0MjksMzE1IDQyOSwzMTMgNDI4LDMxMiA0MjgsMzExIDQyNywzMTAgNDI3LDMwOCA0MjMsMzA0IDQyMiwzMDQgNDIxLDMwMyA0MjAsMzAzIDQxOSwzMDIgNDE4LDMwMiBaIE0gMzk1LDM0MyAzOTUsMzQ0IDM5NCwzNDUgMzk0LDM0NiAzOTMsMzQ3IDM5MywzNTAgMzkyLDM1MSAzOTIsMzU3IDM5MywzNTggMzkzLDM2MSAzOTQsMzYyIDM5NCwzNjMgMzk3LDM2NiAzOTcsMzY3IDM5OCwzNjggMzk5LDM2OCA0MDEsMzcwIDQwMiwzNzAgNDAzLDM3MSA0MDQsMzcxIDQwNSwzNzIgNDA4LDM3MiA0MDksMzczIDQxMywzNzMgNDE0LDM3MiA0MTgsMzcyIDQxOSwzNzEgNDIwLDM3MSA0MjEsMzcwIDQyMiwzNzAgNDI3LDM2NSA0MjcsMzY0IDQyNiwzNjQgNDI1LDM2MyA0MjQsMzYzIDQyMywzNjIgNDIyLDM2MiA0MjEsMzYxIDQxMSwzNjEgNDEwLDM2MiA0MDgsMzYyIDQwNywzNjMgNDA2LDM2MyA0MDQsMzY1IDQwMywzNjQgNDAzLDM2MyA0MDQsMzYyIDQwNCwzNTMgNDAzLDM1MiA0MDMsMzUwIDQwMiwzNDkgNDAyLDM0OCA0MDEsMzQ3IDQwMSwzNDYgMzk3LDM0MiAzOTYsMzQyIFogTSA0MywyODEgNDIsMjgwIDQxLDI4MCA0MCwyODEgMzksMjgxIDM4LDI4MiAzNywyODIgMzUsMjg0IDM0LDI4NCAzMywyODUgMzMsMjg2IDMxLDI4OCAzMSwyODkgMzAsMjkwIDMwLDI5MSAyOSwyOTIgMjksMjk5IDI4LDMwMCAyNywyOTkgMjcsMjk4IDIxLDI5MiAyMCwyOTIgMTksMjkxIDE3LDI5MSAxNiwyOTAgNywyOTAgNiwyOTEgNiwyOTMgNywyOTQgNywyOTUgOCwyOTYgOCwyOTcgMTMsMzAyIDE0LDMwMiAxNSwzMDMgMTYsMzAzIDE3LDMwNCAyMCwzMDQgMjEsMzA1IDI1LDMwNSAyNiwzMDQgMzAsMzA0IDMxLDMwMyAzMywzMDMgMzQsMzAyIDM1LDMwMiA0MSwyOTYgNDEsMjk1IDQyLDI5NCA0MiwyOTIgNDMsMjkxIFogTSA0MjQsMjgxIDQyNCwyOTEgNDI1LDI5MiA0MjUsMjk0IDQyNiwyOTUgNDI2LDI5NiA0MzIsMzAyIDQzMywzMDIgNDM0LDMwMyA0MzYsMzAzIDQzNywzMDQgNDQxLDMwNCA0NDIsMzA1IDQ0NiwzMDUgNDQ3LDMwNCA0NTAsMzA0IDQ1MSwzMDMgNDUyLDMwMyA0NTMsMzAyIDQ1NCwzMDIgNDU5LDI5NyA0NTksMjk2IDQ2MCwyOTUgNDYwLDI5NCA0NjEsMjkzIDQ2MSwyOTEgNDYwLDI5MCA0NTEsMjkwIDQ1MCwyOTEgNDQ4LDI5MSA0NDcsMjkyIDQ0NiwyOTIgNDQwLDI5OCA0NDAsMjk5IDQzOSwzMDAgNDM4LDI5OSA0MzgsMjkyIDQzNywyOTEgNDM3LDI5MCA0MzYsMjg5IDQzNiwyODggNDM0LDI4NiA0MzQsMjg1IDQzMywyODUgNDMwLDI4MiA0MjksMjgyIDQyOCwyODEgNDI3LDI4MSA0MjYsMjgwIDQyNSwyODAgWiBNIDM4LDI1OCAzNSwyNTggMzQsMjU5IDMyLDI1OSAzMCwyNjEgMjksMjYxIDI3LDI2MyAyNywyNjQgMjUsMjY2IDI1LDI2NyAyNCwyNjggMjQsMjY5IDIzLDI3MCAyMywyNzMgMjIsMjc0IDIxLDI3NCAyMCwyNzMgMjAsMjcyIDE0LDI2NiAxMywyNjYgMTIsMjY1IDEwLDI2NSA5LDI2NCAwLDI2NCAwLDI2OCAxLDI2OCAyLDI2OSAyLDI3MCAzLDI3MSAzLDI3MiA5LDI3OCAxMCwyNzggMTEsMjc5IDEzLDI3OSAxNCwyODAgMjMsMjgwIDI0LDI3OSAyNywyNzkgMjgsMjc4IDI5LDI3OCAzMCwyNzcgMzEsMjc3IDM0LDI3NCAzNCwyNzMgMzYsMjcxIDM2LDI3MCAzNywyNjkgMzcsMjY4IDM4LDI2NyBaIE0gMzc5LDM2NCAzNzksMzY1IDM3OCwzNjYgMzc4LDM2OCAzNzcsMzY5IDM3NywzNzggMzc4LDM3OSAzNzgsMzgxIDM3OSwzODIgMzc5LDM4MyAzODYsMzkwIDM4NywzOTAgMzg4LDM5MSAzODksMzkxIDM5MCwzOTIgNDAxLDM5MiA0MDIsMzkxIDQwNCwzOTEgNDA1LDM5MCA0MDYsMzkwIDQwOCwzODggNDA5LDM4OCA0MTAsMzg3IDQxMCwzODUgNDA5LDM4NSA0MDcsMzgzIDQwNiwzODMgNDA1LDM4MiA0MDMsMzgyIDQwMiwzODEgMzkyLDM4MSAzOTEsMzgyIDM5MCwzODIgMzg5LDM4MyAzODgsMzgzIDM4NywzODIgMzg3LDM4MSAzODgsMzgwIDM4OCwzNzcgMzg5LDM3NiAzODksMzcxIDM4OCwzNzAgMzg4LDM2OCAzODcsMzY3IDM4NywzNjYgMzg2LDM2NSAzODYsMzY0IDM4MywzNjEgMzgyLDM2MSBaIE0gNDA3LDMyNCA0MDcsMzI1IDQwNiwzMjYgNDA2LDMyOCA0MDUsMzI5IDQwNSwzMzUgNDA2LDMzNiA0MDYsMzM5IDQwNywzNDAgNDA3LDM0MSA0MDgsMzQyIDQwOCwzNDMgNDE0LDM0OSA0MTUsMzQ5IDQxNiwzNTAgNDE4LDM1MCA0MTksMzUxIDQzMCwzNTEgNDMxLDM1MCA0MzIsMzUwIDQzMywzNDkgNDM0LDM0OSA0MzYsMzQ3IDQzNywzNDcgNDQwLDM0NCA0NDAsMzQzIDQ0MSwzNDIgNDQxLDM0MSA0NDAsMzQxIDQzOSwzNDAgNDM4LDM0MCA0MzcsMzM5IDQyNywzMzkgNDI2LDM0MCA0MjQsMzQwIDQyMywzNDEgNDIyLDM0MSA0MjAsMzQzIDQxOSwzNDMgNDE4LDM0NCA0MTcsMzQzIDQxNywzNDEgNDE4LDM0MCA0MTgsMzM3IDQxNywzMzYgNDE3LDMzMyA0MTYsMzMyIDQxNiwzMzEgNDE1LDMzMCA0MTUsMzI5IDQxMiwzMjYgNDEyLDMyNSA0MTEsMzI1IDQwOSwzMjMgNDA4LDMyMyBaIE0gNTksMzI0IDU4LDMyMyA1NywzMjMgNTYsMzI0IDU1LDMyNCA1MiwzMjcgNTIsMzI4IDUxLDMyOSA1MSwzMzAgNTAsMzMxIDUwLDMzMyA0OSwzMzQgNDksMzM3IDQ4LDMzOCA0OCwzNDAgNDksMzQxIDQ5LDM0MyA0OCwzNDQgNDYsMzQyIDQ1LDM0MiA0MywzNDAgNDAsMzQwIDM5LDMzOSAyOSwzMzkgMjgsMzQwIDI3LDM0MCAyNiwzNDEgMjYsMzQzIDMyLDM0OSAzMywzNDkgMzQsMzUwIDM2LDM1MCAzNywzNTEgNDcsMzUxIDQ4LDM1MCA1MCwzNTAgNTEsMzQ5IDUyLDM0OSA1OCwzNDMgNTgsMzQyIDYwLDM0MCA2MCwzMzggNjEsMzM3IDYxLDMyOSA2MCwzMjggNjAsMzI2IDU5LDMyNSBaIE0gNDksODkgNDksOTAgNDgsOTEgNDgsOTMgNDksOTQgNTAsOTQgNTIsOTYgNTMsOTYgNTYsOTkgNTcsOTkgNTksMTAxIDYwLDEwMSA2MywxMDQgNjIsMTA1IDYxLDEwNSA2MCwxMDQgNTYsMTA0IDU1LDEwMyA1MiwxMDMgNTEsMTAyIDQ4LDEwMiA0NywxMDEgNDQsMTAxIDQzLDEwMCA0MSwxMDAgNDAsMTAxIDQwLDEwMiAzOCwxMDQgMzgsMTA1IDQwLDEwNyA0MSwxMDcgNDQsMTEwIDQ1LDExMCA0NywxMTIgNDgsMTEyIDUxLDExNSA1MiwxMTUgNTUsMTE4IDU2LDExOCA1OCwxMjAgNTksMTIwIDYyLDEyMyA2NCwxMjMgNjYsMTIxIDY2LDExOSA2NSwxMTkgNjMsMTE3IDYyLDExNyA2MCwxMTUgNTksMTE1IDU2LDExMiA1NSwxMTIgNTMsMTEwIDUyLDExMCA1MCwxMDggNTEsMTA3IDUzLDEwNyA1NCwxMDggNTcsMTA4IDU4LDEwOSA2MiwxMDkgNjMsMTEwIDY2LDExMCA2NywxMTEgNzAsMTExIDcxLDExMiA3MywxMTIgNzMsMTExIDc1LDEwOSA3NSwxMDYgNzQsMTA2IDcxLDEwMyA3MCwxMDMgNjcsMTAwIDY2LDEwMCA2Myw5NyA2Miw5NyA1OSw5NCA1OCw5NCA1Niw5MiA1NSw5MiA1Miw4OSBaIE0gNDI5LDI1OCA0MjksMjY3IDQzMCwyNjggNDMwLDI2OSA0MzEsMjcwIDQzMSwyNzEgNDMzLDI3MyA0MzMsMjc0IDQzNiwyNzcgNDM3LDI3NyA0MzgsMjc4IDQzOSwyNzggNDQwLDI3OSA0NDMsMjc5IDQ0NCwyODAgNDUzLDI4MCA0NTQsMjc5IDQ1NSwyNzkgNDU2LDI3OCA0NTgsMjc4IDQ2NCwyNzIgNDY0LDI3MSA0NjUsMjcwIDQ2NSwyNjQgNDU4LDI2NCA0NTcsMjY1IDQ1NSwyNjUgNDU0LDI2NiA0NTMsMjY2IDQ0NywyNzIgNDQ3LDI3MyA0NDUsMjc1IDQ0NCwyNzQgNDQ0LDI3MCA0NDMsMjY5IDQ0MywyNjggNDQyLDI2NyA0NDIsMjY2IDQ0MCwyNjQgNDQwLDI2MyA0MzgsMjYxIDQzNywyNjEgNDM1LDI1OSA0MzQsMjU5IDQzMywyNTggWiBNIDg1LDM2MSA4MywzNjEgODEsMzYzIDgxLDM2NCA3OSwzNjYgNzksMzY4IDc4LDM2OSA3OCwzNzggNzksMzc5IDc5LDM4MSA4MCwzODIgODAsMzgzIDc5LDM4NCA3OCwzODMgNzcsMzgzIDc2LDM4MiA3NSwzODIgNzQsMzgxIDY0LDM4MSA2MywzODIgNjEsMzgyIDYwLDM4MyA1OSwzODMgNTcsMzg1IDU3LDM4NyA1OSwzODkgNjAsMzg5IDYyLDM5MSA2NCwzOTEgNjUsMzkyIDc2LDM5MiA3NywzOTEgNzgsMzkxIDc5LDM5MCA4MCwzOTAgODEsMzg5IDgyLDM4OSA4NiwzODUgODYsMzg0IDg3LDM4MyA4NywzODIgODgsMzgxIDg4LDM3OSA4OSwzNzggODksMzY4IDg4LDM2NyA4OCwzNjYgODcsMzY1IDg3LDM2NCA4NiwzNjMgODYsMzYyIFogTSA3Miw2NCA2Nyw2OSA2Nyw3MCA2Niw3MSA2Niw3MyA2NSw3NCA2NSw3OCA2Niw3OSA2Niw4MSA2Nyw4MiA2Nyw4MyA2OCw4NCA2OCw4NSA3NCw5MSA3NSw5MSA3Nyw5MyA3OCw5MyA3OSw5NCA4Niw5NCA4Nyw5MyA4OSw5MyA5Miw5MCA5Myw5MCA5NCw4OSA5NCw4OCA5Nyw4NSA5Nyw4MiA4Niw3MSA4NSw3MSA3OSw3NyA3OSw4MCA4MSw4MiA4Miw4MiA4NSw3OSA4Niw3OSA5MSw4NCA4Nyw4OCA4Niw4OCA4NSw4OSA4Miw4OSA4MSw4OCA3OSw4OCA3OCw4NyA3Nyw4NyA3Myw4MyA3Myw4MiA3Miw4MSA3Miw4MCA3MSw3OSA3MSw3MyA3Miw3MiA3Miw3MSA3NSw2OCA3Niw2OCA3Nyw2NyA3OCw2NyA3OCw2NSA3Niw2MyA3NCw2MyA3Myw2NCBaIE0gMjkzLDEwIDI5MSwxMiAyOTAsMTIgMjg2LDE2IDI4NiwxNyAyODUsMTggMjg1LDE5IDI4NCwyMCAyODQsMjIgMjgzLDIzIDI4MywyNyAyODIsMjggMjgyLDMwIDI4MywzMSAyODMsMzQgMjg0LDM1IDI4NCwzNiAyODksNDEgMjkxLDQxIDI5Miw0MiAyOTcsNDIgMjk4LDQzIDMwMSw0MyAzMDEsNDIgMzAyLDQxIDMwMiwzOCAzMDMsMzcgMzAzLDM0IDMwNCwzMyAzMDQsMzAgMzA1LDI5IDMwNSwyNiAzMDMsMjYgMzAyLDI1IDMwMCwyNSAyOTksMjQgMjk1LDI0IDI5NSwyOSAyOTgsMjkgMjk5LDMwIDI5OSwzMyAyOTgsMzQgMjk4LDM2IDI5NiwzOCAyOTUsMzggMjk0LDM3IDI5MiwzNyAyODksMzQgMjg5LDMzIDI4OCwzMiAyODgsMjUgMjg5LDI0IDI4OSwyMiAyOTAsMjEgMjkwLDIwIDI5NCwxNiAyOTUsMTYgMjk2LDE1IDMwMSwxNSAzMDIsMTYgMzAzLDE2IDMwNSwxOCAzMDcsMTggMzA3LDE3IDMwOCwxNiAzMDgsMTQgMzA2LDEyIDMwNSwxMiAzMDQsMTEgMzAyLDExIDMwMSwxMCBaIE0gMjQxLDM2NiAyNDAsMzY3IDI0MCwzNzEgMjQzLDM3MSAyNDQsMzcwIDI1MSwzNzAgMjUzLDM3MiAyNTMsMzc2IDI1MiwzNzcgMjUyLDM3OCAyNTAsMzgwIDI1MCwzODEgMjM5LDM5MiAyMzksMzk3IDI2MSwzOTcgMjYxLDM5MiAyNTAsMzkyIDI0OSwzOTEgMjU0LDM4NiAyNTQsMzg1IDI1NywzODIgMjU3LDM4MSAyNTgsMzgwIDI1OCwzNzkgMjU5LDM3OCAyNTksMzc2IDI2MCwzNzUgMjYwLDM3MiAyNTksMzcxIDI1OSwzNjkgMjU4LDM2OCAyNTgsMzY3IDI1NywzNjYgMjU2LDM2NiAyNTUsMzY1IDI1NCwzNjUgMjUzLDM2NCAyNDcsMzY0IDI0NiwzNjUgMjQzLDM2NSAyNDIsMzY2IFogTSAzMjQsMTkgMzI0LDIwIDMyMywyMSAzMjMsMjIgMzIyLDIzIDMyMiwyNCAzMjEsMjUgMzIxLDI2IDMyMCwyNyAzMjAsMjggMzE5LDI5IDMxOSwzMCAzMTgsMzEgMzE4LDMyIDMxNywzMyAzMTcsMzQgMzE2LDM1IDMxNiwzNyAzMTUsMzggMzE1LDM5IDMxNCw0MCAzMTQsNDEgMzEzLDQyIDMxMyw0MyAzMTIsNDQgMzEyLDQ1IDMxMSw0NiAzMTEsNDcgMzEyLDQ4IDMxMyw0OCAzMTQsNDkgMzE1LDQ5IDMxNiw0OCAzMTYsNDcgMzE3LDQ2IDMxNyw0NSAzMTgsNDQgMzE4LDQzIDMxOSw0MiAzMTksNDEgMzIwLDQwIDMyMCwzOSAzMjEsMzggMzI0LDM4IDMyNSwzOSAzMjYsMzkgMzI3LDQwIDMyOSw0MCAzMzAsNDEgMzMwLDQzIDMyOSw0NCAzMjksNDUgMzI4LDQ2IDMyOCw0OCAzMjcsNDkgMzI3LDUwIDMyNiw1MSAzMjYsNTIgMzI1LDUzIDMyNSw1NCAzMjYsNTUgMzI3LDU1IDMyOCw1NiAzMjksNTYgMzMwLDU1IDMzMCw1NCAzMzEsNTMgMzMxLDUyIDMzMiw1MSAzMzIsNDkgMzMzLDQ4IDMzMyw0NyAzMzQsNDYgMzM0LDQ1IDMzNSw0NCAzMzUsNDMgMzM2LDQyIDMzNiw0MSAzMzcsNDAgMzM3LDM5IDMzOCwzOCAzMzgsMzcgMzM5LDM2IDMzOSwzNSAzNDAsMzQgMzQwLDMzIDM0MSwzMiAzNDEsMzEgMzQyLDMwIDM0MiwyOSAzNDMsMjggMzQzLDI3IDM0MiwyNyAzNDEsMjYgMzM4LDI2IDMzOCwyNyAzMzcsMjggMzM3LDI5IDMzNiwzMCAzMzYsMzEgMzM1LDMyIDMzNSwzMyAzMzQsMzQgMzM0LDM1IDMzMywzNiAzMzEsMzYgMzMwLDM1IDMyOSwzNSAzMjgsMzQgMzI3LDM0IDMyNiwzMyAzMjUsMzMgMzI0LDMyIDMyNCwzMSAzMjUsMzAgMzI1LDI5IDMyNiwyOCAzMjYsMjcgMzI3LDI2IDMyNywyNSAzMjgsMjQgMzI4LDIzIDMyOSwyMiAzMjksMjEgMzI4LDIxIDMyNywyMCAzMjYsMjAgMzI1LDE5IFogTSA0MTgsOTAgNDE3LDkwIDQxNiw5MSA0MTUsOTEgNDEzLDkzIDQxMiw5MyA0MTAsOTUgNDA5LDk1IDQwNiw5OCA0MDUsOTggNDAzLDEwMCA0MDIsMTAwIDQwMCwxMDIgMzk5LDEwMiAzOTcsMTA0IDM5NiwxMDQgMzkzLDEwNyAzOTIsMTA3IDM5MiwxMDggMzkzLDEwOSAzOTMsMTEwIDM5NCwxMTEgMzk0LDExMiAzOTUsMTEyIDM5OCwxMDkgMzk5LDEwOSA0MDEsMTA3IDQwMiwxMDcgNDA0LDEwNSA0MDUsMTA1IDQwNiwxMDQgNDA5LDEwNyA0MDksMTA4IDQxMiwxMTEgNDEyLDExMiA0MTAsMTE0IDQwOSwxMTQgNDA2LDExNyA0MDUsMTE3IDQwMywxMTkgNDAyLDExOSA0MDEsMTIwIDQwMSwxMjEgNDAzLDEyMyA0MDYsMTIzIDQwOSwxMjAgNDEwLDEyMCA0MTIsMTE4IDQxMywxMTggNDE2LDExNSA0MTcsMTE1IDQyMCwxMTIgNDIxLDExMiA0MjQsMTA5IDQyNSwxMDkgNDI4LDEwNiA0MjksMTA2IDQyOSwxMDQgNDI3LDEwMiA0MjYsMTAyIDQyNSwxMDMgNDI0LDEwMyA0MjIsMTA1IDQyMSwxMDUgNDE4LDEwOCA0MTYsMTA4IDQxMywxMDUgNDEzLDEwNCA0MTAsMTAxIDQxMiw5OSA0MTMsOTkgNDE2LDk2IDQxNyw5NiA0MjAsOTMgNDIwLDkyIFogTSAyMzQsMCAyMzQsMTIgMjMzLDEzIDIzMywzMyAyMzcsMzMgMjM3LDI5IDIzOCwyOCAyMzgsMjAgMjM5LDE5IDI0OCwxOSAyNDksMjAgMjQ5LDIzIDI0OCwyNCAyNDgsMzMgMjUzLDMzIDI1MywxOSAyNTQsMTggMjU0LDIgMjQ5LDIgMjQ5LDE0IDI0OCwxNSAyNDcsMTQgMjM5LDE0IDIzOCwxMyAyMzksMTIgMjM5LDAgWiBNIDIwMCwzIDE5NywzIDE5Niw0IDE5NSw0IDE5NCw1IDE5NCw3IDE5Myw4IDE5Myw5IDE5MiwxMCAxOTIsMTIgMTkxLDEzIDE5MSwxNCAxOTAsMTUgMTkwLDE2IDE4OSwxNyAxODgsMTcgMTg3LDE2IDE4NywxMiAxODYsMTEgMTg2LDcgMTg1LDYgMTgyLDYgMTgxLDcgMTgxLDExIDE4MiwxMiAxODIsMTYgMTgzLDE3IDE4MywyMSAxODQsMjIgMTg0LDI2IDE4NSwyNyAxODUsMzEgMTg2LDMyIDE4NiwzNyAxODcsMzggMTg4LDM4IDE4OSwzNyAxOTEsMzcgMTkxLDMyIDE5MCwzMSAxOTAsMjcgMTg5LDI2IDE4OSwyNSAxOTAsMjQgMTk1LDI5IDE5NSwzMCAyMDAsMzUgMjA1LDM1IDIwNiwzNCAyMDYsMzMgMjAyLDI5IDIwMiwyOCAxOTMsMTkgMTk0LDE4IDE5NCwxNyAxOTUsMTYgMTk1LDE1IDE5NiwxNCAxOTYsMTMgMTk3LDEyIDE5NywxMSAxOTgsMTAgMTk4LDkgMTk5LDggMTk5LDcgMjAwLDYgWiBNIDQsMTg0IDQsMTg1IDMsMTg2IDMsMTg5IDEwLDE5NiAxMSwxOTYgMTQsMTk5IDEzLDIwMCAxMiwyMDAgMTEsMTk5IDUsMTk5IDQsMTk4IDIsMTk4IDIsMTk5IDEsMjAwIDAsMjAwIDAsMjAzIDMsMjAzIDQsMjA0IDksMjA0IDEwLDIwNSAxNSwyMDUgMTYsMjA2IDIxLDIwNiAyMiwyMDcgMjcsMjA3IDI4LDIwOCAzMiwyMDggMzIsMjA3IDMzLDIwNiAzMywyMDQgMzIsMjAzIDI4LDIwMyAyNywyMDIgMjIsMjAyIDIxLDIwMSAyMSwyMDAgMjIsMTk5IDIzLDE5OSAyNCwxOTggMjYsMTk4IDI3LDE5NyAyOCwxOTcgMjksMTk2IDMwLDE5NiAzMSwxOTUgMzMsMTk1IDM1LDE5MyAzNSwxODkgMzIsMTg5IDMxLDE5MCAzMCwxOTAgMjksMTkxIDI4LDE5MSAyNywxOTIgMjUsMTkyIDI0LDE5MyAyMywxOTMgMjIsMTk0IDIxLDE5NCAyMCwxOTUgMTcsMTk1IDE2LDE5NCAxNSwxOTQgNSwxODQgWiBNIDI5LDExOSAyOCwxMjAgMjgsMTIxIDI3LDEyMiAyNywxMjMgMjgsMTI0IDI5LDEyNCAzMCwxMjUgMzEsMTI1IDMyLDEyNiAzMywxMjYgMzQsMTI3IDM1LDEyNyAzNiwxMjggMzcsMTI4IDM4LDEyOSAzOSwxMjkgNDAsMTMwIDQxLDEzMCA0MiwxMzEgNDMsMTMxIDQ0LDEzMiA0NSwxMzIgNDcsMTM0IDQ4LDEzNCA0OSwxMzUgNDksMTM2IDUwLDEzNyA1MCwxMzkgNDksMTQwIDQ5LDE0MSA0OCwxNDIgNDcsMTQyIDQ2LDE0MyA0MywxNDMgNDIsMTQyIDQwLDE0MiAzOSwxNDEgMzgsMTQxIDM3LDE0MCAzNiwxNDAgMzUsMTM5IDM0LDEzOSAzMywxMzggMzIsMTM4IDMxLDEzNyAzMCwxMzcgMjksMTM2IDI4LDEzNiAyNywxMzUgMjYsMTM1IDI1LDEzNCAyNCwxMzQgMjMsMTMzIDIyLDEzMyAyMSwxMzQgMjEsMTM1IDIwLDEzNiAyMCwxMzcgMjEsMTM4IDIyLDEzOCAyMywxMzkgMjQsMTM5IDI1LDE0MCAyNiwxNDAgMjcsMTQxIDI4LDE0MSAyOSwxNDIgMzAsMTQyIDMxLDE0MyAzMiwxNDMgMzMsMTQ0IDM0LDE0NCAzNSwxNDUgMzcsMTQ1IDM4LDE0NiAzOSwxNDYgNDAsMTQ3IDQyLDE0NyA0MywxNDggNDgsMTQ4IDQ5LDE0NyA1MCwxNDcgNTMsMTQ0IDUzLDE0MyA1NCwxNDIgNTQsMTQwIDU1LDEzOSA1NSwxMzYgNTQsMTM1IDU0LDEzMyA1MCwxMjkgNDksMTI5IDQ4LDEyOCA0NywxMjggNDYsMTI3IDQ1LDEyNyA0NCwxMjYgNDMsMTI2IDQxLDEyNCA0MCwxMjQgMzksMTIzIDM4LDEyMyAzNywxMjIgMzYsMTIyIDM1LDEyMSAzNCwxMjEgMzMsMTIwIDMyLDEyMCAzMSwxMTkgWiBNIDE5MSw0NDMgMTkxLDQ0OCAxOTAsNDQ5IDE5MCw0NTYgMTg5LDQ1NyAxODksNDYyIDE5Miw0NjIgMTkzLDQ2MyAxOTQsNDYzIDE5NCw0NjEgMTk1LDQ2MCAxOTUsNDUyIDE5Niw0NTEgMTk2LDQ0OCAxOTcsNDQ3IDE5OCw0NDcgMTk5LDQ0OCAyMDcsNDQ4IDIwOCw0NDkgMjE2LDQ0OSAyMTcsNDUwIDIxOSw0NTAgMjIwLDQ1MSAyMjAsNDU3IDIxOSw0NTggMjE5LDQ1OSAyMTgsNDYwIDIxNyw0NjAgMjE3LDQ2NCAyMjMsNDY0IDIyNCw0NjMgMjI0LDQ2MCAyMjUsNDU5IDIyNSw0NTIgMjI2LDQ1MSAyMjYsNDQ3IDIyNSw0NDYgMjE3LDQ0NiAyMTYsNDQ1IDIwNyw0NDUgMjA2LDQ0NCAxOTgsNDQ0IDE5Nyw0NDMgWiBNIDM3OCw0OSAzNzcsNDkgMzc2LDQ4IDM3Miw0OCAzNzEsNDkgMzY5LDQ5IDM2NSw1MyAzNjUsNTQgMzY0LDU1IDM2NCw2MSAzNjUsNjIgMzY1LDYzIDM2Niw2NCAzNjYsNjYgMzY3LDY3IDM2Nyw2OSAzNjYsNzAgMzY2LDcxIDM2NSw3MiAzNjEsNzIgMzU3LDY4IDM1Nyw2NyAzNTUsNjcgMzU0LDY4IDM1NCw2OSAzNTMsNzAgMzUzLDcxIDM1NSw3MyAzNTUsNzQgMzU2LDc0IDM1OCw3NiAzNTksNzYgMzYwLDc3IDM2Miw3NyAzNjMsNzggMzY0LDc4IDM2NSw3NyAzNjcsNzcgMzcxLDczIDM3MSw3MiAzNzIsNzEgMzcyLDY5IDM3Myw2OCAzNzMsNjcgMzcyLDY2IDM3Miw2NCAzNzEsNjMgMzcxLDYyIDM3MCw2MSAzNzAsNTYgMzcyLDU0IDM3Niw1NCAzNzksNTcgMzc5LDU4IDM4MSw1OCAzODMsNTYgMzgzLDU1IDM4Miw1NCAzODIsNTMgWiBNIDI3NywzNjUgMjc2LDM2NiAyNzUsMzY2IDI3MiwzNjkgMjcxLDM2OSAyNjgsMzcyIDI2NywzNzIgMjY3LDM3MyAyNzAsMzc2IDI3MCwzNzcgMjcxLDM3NyAyNzUsMzczIDI3NiwzNzQgMjc2LDM5NyAyODMsMzk3IDI4MywzNjUgWiBNIDQwMyw3MiA0MDIsNzIgNDAxLDcxIDQwMCw3MSAzOTksNzAgMzkxLDcwIDM5MCw3MSAzODksNzEgMzg4LDcyIDM4Nyw3MiAzODQsNzUgMzgzLDc1IDM4MSw3NyAzODEsNzggMzc5LDgwIDM3OSw4MSAzNzgsODIgMzc4LDgzIDM3Nyw4NCAzNzcsOTAgMzc4LDkxIDM3OCw5MyAzNzksOTQgMzc5LDk1IDM4Miw5OCAzODMsOTggMzg1LDEwMCAzODYsMTAwIDM4OSw5NyAzODksOTYgMzg4LDk2IDM4Myw5MSAzODMsODkgMzgyLDg4IDM4Myw4NyAzODMsODQgMzg1LDgyIDM4NSw4MSAzODksNzcgMzkwLDc3IDM5MSw3NiAzOTIsNzYgMzkzLDc1IDM5OCw3NSAzOTksNzYgNDAwLDc2IDQwMyw3OSA0MDMsODAgNDA0LDgxIDQwNCw4MiA0MDUsODIgNDA4LDc5IDQwOCw3OCA0MDcsNzcgNDA3LDc2IFogTSAxODksMzY1IDE4NCwzNzAgMTgzLDM3MCAxODEsMzcyIDE4MSwzNzMgMTgyLDM3NCAxODIsMzc1IDE4MywzNzYgMTg1LDM3NiAxODcsMzc0IDE4OCwzNzQgMTg5LDM3NSAxODksMzk3IDE5NiwzOTcgMTk2LDM2NSBaIE0gMTYzLDExIDE2MiwxMiAxNjAsMTIgMTU5LDEzIDE1OCwxMyAxNTQsMTcgMTU0LDE4IDE1MywxOSAxNTMsMjEgMTUyLDIyIDE1MiwyNyAxNTMsMjggMTUzLDMxIDE1NCwzMiAxNTQsMzQgMTU1LDM1IDE1NSwzNiAxNTcsMzggMTU3LDM5IDE1OSw0MSAxNjAsNDEgMTYxLDQyIDE2Miw0MiAxNjMsNDMgMTcyLDQzIDE3Myw0MiAxNzQsNDIgMTc1LDQxIDE3Niw0MSAxNzcsNDAgMTc3LDM4IDE3NiwzNyAxNzYsMzYgMTc0LDM2IDE3MywzNyAxNzIsMzcgMTcxLDM4IDE2NSwzOCAxNTksMzIgMTU5LDMwIDE1OCwyOSAxNTgsMjEgMTU5LDIwIDE1OSwxOSAxNjIsMTYgMTY4LDE2IDE2OCwxMiAxNjcsMTEgWiBNIDQ1MywxNjUgNDUzLDE2NiA0NTQsMTY3IDQ1NCwxNzAgNDUzLDE3MSA0NTMsMTcyIDQ1MCwxNzUgNDQ5LDE3NSA0NDgsMTc2IDQ0NywxNzYgNDQ2LDE3NyA0NDUsMTc3IDQ0NCwxNzggNDM2LDE3OCA0MzUsMTc3IDQzNCwxNzcgNDMyLDE3NSA0MzIsMTcyIDQzMSwxNzEgNDMyLDE3MCA0MzIsMTY5IDQzNiwxNjUgNDM3LDE2NSA0MzgsMTY0IDQzOSwxNjQgNDQwLDE2MyA0NDUsMTYzIDQ0NiwxNjIgNDQ4LDE2MiA0NDksMTYzIDQ1MSwxNjMgWiBNIDQ0MCwxMzIgNDQwLDEzNiA0MzksMTM3IDQzOSwxMzggNDM2LDE0MSA0MzUsMTQxIDQzMywxNDMgNDMyLDE0MyA0MzEsMTQ0IDQyOSwxNDQgNDI4LDE0NSA0MjIsMTQ1IDQxOSwxNDIgNDE5LDE0MSA0MTgsMTQwIDQxOCwxMzcgNDIwLDEzNSA0MjAsMTM0IDQyMSwxMzMgNDIyLDEzMyA0MjQsMTMxIDQyNSwxMzEgNDI2LDEzMCA0MjcsMTMwIDQyOCwxMjkgNDMxLDEyOSA0MzIsMTI4IDQzNSwxMjggNDM2LDEyOSA0MzcsMTI5IFogTSAxMjgsMzEgMTMyLDMxIDEzOCwzNyAxMzgsMzggMTM5LDM5IDEzOSw0MCAxNDAsNDEgMTQwLDQ5IDEzNyw1MiAxMzYsNTIgMTM1LDUzIDEzNCw1MiAxMzIsNTIgMTMxLDUxIDEzMCw1MSAxMjgsNDkgMTI4LDQ4IDEyNiw0NiAxMjYsNDUgMTI0LDQzIDEyNCw0MCAxMjMsMzkgMTIzLDM2IDEyNCwzNSAxMjQsMzQgMTI2LDMyIDEyNywzMiBaIE0gMTQsMTUwIDE0LDE1MiAxMywxNTMgMTMsMTU1IDE3LDE1OSAxOCwxNTkgMjMsMTY0IDIyLDE2NSAxNSwxNjUgMTQsMTY2IDksMTY2IDksMTY3IDgsMTY4IDgsMTY5IDcsMTcwIDcsMTcyIDgsMTcyIDksMTcxIDE1LDE3MSAxNiwxNzAgMjMsMTcwIDI0LDE2OSAzMCwxNjkgMzEsMTcwIDMzLDE3MCAzNCwxNzEgMzYsMTcxIDM3LDE3MiA0MCwxNzIgNDEsMTcxIDQxLDE2OCA0MCwxNjcgMzgsMTY3IDM3LDE2NiAzNSwxNjYgMzQsMTY1IDMyLDE2NSAzMSwxNjQgMzAsMTY0IDIxLDE1NSAyMCwxNTUgMTUsMTUwIFogTSAxOTgsNDMxIDE5OCw0MzggMTk3LDQzOSAxOTcsNDQxIDIwMiw0NDEgMjAzLDQ0MiAyMTAsNDQyIDIxMSw0NDMgMjIxLDQ0MyAyMjEsNDMzIDIxNSw0MzMgMjE0LDQzMiAyMDcsNDMyIDIwNiw0MzEgWiBNIDQ1MSwyMzQgNDQ4LDIzNCA0NDgsMjM1IDQ0NSwyMzggNDQ1LDIzOSA0NDQsMjQwIDQ0NCwyNDIgNDQzLDI0MyA0NDMsMjUyIDQ0NCwyNTMgNDQ0LDI1NiA0NDUsMjU3IDQ0NSwyNTggNDQ3LDI2MCA0NDgsMjYwIDQ1MiwyNTYgNDUyLDI1NSA0NTMsMjU0IDQ1MywyNTMgNDU0LDI1MiA0NTQsMjQ5IDQ1NSwyNDggNDU1LDI0NCA0NTQsMjQzIDQ1NCwyNDAgNDUzLDIzOSA0NTMsMjM4IDQ1MiwyMzcgNDUyLDIzNiA0NTEsMjM1IFogTSAxNiwyMzQgMTYsMjM1IDE1LDIzNiAxNSwyMzcgMTQsMjM4IDE0LDIzOSAxMywyNDAgMTMsMjQyIDEyLDI0MyAxMiwyNDggMTMsMjQ5IDEzLDI1MiAxNCwyNTMgMTQsMjU0IDE1LDI1NSAxNSwyNTYgMTksMjYwIDIwLDI2MCAyMSwyNTkgMjEsMjU4IDIyLDI1NyAyMiwyNTYgMjMsMjU1IDIzLDI1MyAyNCwyNTIgMjQsMjQ0IDIzLDI0MyAyMywyNDAgMjIsMjM5IDIyLDIzOCAxOCwyMzQgWiBNIDQ2NSwxOTIgNDYxLDE5MiA0NjAsMTkzIDQ1NSwxOTMgNDU0LDE5NCA0NDgsMTk0IDQ0NywxOTUgNDQyLDE5NSA0NDEsMTk2IDQzNiwxOTYgNDM1LDE5NyA0MzMsMTk3IDQzMywxOTkgNDM0LDIwMCA0MzQsMjA2IDQzNSwyMDcgNDM1LDIxMSA0NDAsMjExIDQ0MCwyMDggNDM5LDIwNyA0MzksMjAyIDQ0MCwyMDEgNDQyLDIwMSA0NDMsMjAwIDQ0OCwyMDAgNDQ5LDE5OSA0NTQsMTk5IDQ1NSwxOTggNDYwLDE5OCA0NjEsMTk3IDQ2NSwxOTcgWiBNIDM0OCwzOTcgMzQ5LDM5OCAzNDksNDAwIDM0OCw0MDEgMzQ4LDQwMyAzNDcsNDA0IDM0Nyw0MDcgMzQ5LDQwNyAzNTAsNDA4IDM1MSw0MDggMzUyLDQwNyAzNTIsNDA1IDM1Myw0MDQgMzU0LDQwNSAzNTQsNDA4IDM1Nyw0MTEgMzU4LDQxMSAzNTksNDEyIDM2MCw0MTIgMzYyLDQxNCAzNjIsNDE1IDM2MSw0MTYgMzYxLDQxNyAzNjAsNDE4IDM2MCw0MTkgMzU5LDQyMCAzNTksNDIxIDM1OCw0MjIgMzU4LDQyMyAzNTcsNDI0IDM1Nyw0MjUgMzU2LDQyNiAzNTQsNDI0IDM1NCw0MjMgMzUyLDQyMSAzNTIsNDIwIDM0OSw0MTcgMzQ5LDQxNiAzNTAsNDE1IDM1MSw0MTUgMzUxLDQxMCAzNDgsNDEwIDM0Nyw0MDkgMzQ2LDQwOSAzNDUsNDA4IDM0NCw0MDggMzQyLDQwNiAzNDIsNDA0IDM0Myw0MDMgMzQzLDQwMiAzNDIsNDAxIDM0Myw0MDAgMzQ0LDQwMCAzNDUsMzk5IDM0NiwzOTkgWiBNIDE2NCw0MjAgMTYzLDQyMSAxNjMsNDIyIDE2Miw0MjMgMTYyLDQyNSAxNjEsNDI2IDE2MSw0MjcgMTYwLDQyOCAxNjAsNDMwIDE2MSw0MzAgMTYyLDQzMSAxNjQsNDMxIDE2NSw0MzIgMTY3LDQzMiAxNjgsNDMzIDE3MCw0MzMgMTcxLDQzNCAxNzIsNDM0IDE3Myw0MzUgMTc3LDQzNSAxNzcsNDM0IDE3OCw0MzMgMTc4LDQzMSAxNzksNDMwIDE3OSw0MjkgMTgwLDQyOCAxODAsNDI2IDE3OSw0MjYgMTc4LDQyNSAxNzcsNDI1IDE3Niw0MjQgMTc0LDQyNCAxNzMsNDIzIDE3MSw0MjMgMTcwLDQyMiAxNjksNDIyIDE2OCw0MjEgMTY2LDQyMSAxNjUsNDIwIFogTSAxOTksNDUwIDE5OSw0NTQgMTk4LDQ1NSAxOTgsNDYwIDE5OSw0NjEgMjA4LDQ2MSAyMDksNDYyIDIxNSw0NjIgMjE1LDQ1OCAyMTYsNDU3IDIxNiw0NTIgMjE1LDQ1MSAyMDQsNDUxIDIwMyw0NTAgWiBNIDE5Miw0MjYgMTkyLDQyOCAxOTksNDI4IDIwMCw0MjkgMjA3LDQyOSAyMDgsNDMwIDIxNiw0MzAgMjE3LDQzMSAyMjQsNDMxIDIyNSw0MzIgMjI4LDQzMiAyMjksNDMxIDIyOSw0MjggMjI3LDQyOCAyMjYsNDI3IDIxOCw0MjcgMjE3LDQyNiAyMTUsNDI2IDIxNCw0MjUgMjE0LDQyMiAyMTAsNDIyIDIwOSw0MjEgMjA4LDQyMSAyMDgsNDI0IDIwNyw0MjUgMTk5LDQyNSAxOTgsNDI0IDE5Myw0MjQgMTkzLDQyNSBaIE0gMjczLDQgMjY5LDQgMjY5LDggMjY4LDkgMjY4LDE1IDI2NywxNiAyNjcsMjEgMjY2LDIyIDI2NiwyNyAyNjUsMjggMjY1LDMzIDI2NCwzNCAyNjQsMzUgMjY5LDM1IDI2OSwzNCAyNzAsMzMgMjcwLDI4IDI3MSwyNyAyNzEsMjIgMjcyLDIxIDI3MiwxNiAyNzMsMTUgMjczLDkgMjc0LDggMjc0LDUgWiBNIDI2MSwyOTMgMjYyLDI5MiAyNzEsMjkyIDI3MiwyOTMgMjcyLDMwMiAyNzEsMzAzIDI2MiwzMDMgMjYxLDMwMiBaIE0gMjYxLDI1OSAyNjIsMjU4IDI3MSwyNTggMjcyLDI1OSAyNzIsMjY4IDI3MSwyNjkgMjYyLDI2OSAyNjEsMjY4IFogTSAyOTgsMjkzIDI5OSwyOTIgMzA3LDI5MiAzMDgsMjkzIDMwOCwzMDIgMzA3LDMwMyAyOTksMzAzIDI5OCwzMDIgWiBNIDI5OCwyNTkgMjk5LDI1OCAzMDcsMjU4IDMwOCwyNTkgMzA4LDI2OCAzMDcsMjY5IDI5OSwyNjkgMjk4LDI2OCBaIE0gMzQ5LDM5NyAzNTEsMzk1IDM1MiwzOTUgMzU0LDM5MyAzNTUsMzkzIDM1NiwzOTIgMzU3LDM5MyAzNTcsMzk2IDM1OCwzOTcgMzYzLDM5NyAzNjQsMzk4IDM2MywzOTkgMzYyLDM5OSAzNjIsNDAzIDM2Myw0MDQgMzYzLDQwNiAzNjIsNDA3IDM2MSw0MDcgMzYwLDQwNiAzNTksNDA2IDM1Nyw0MDQgMzU1LDQwNCAzNTQsNDA1IDM1Myw0MDQgMzUzLDM5OCAzNTAsMzk4IFogTSAxNjMsNDE1IDE2Myw0MTcgMTY0LDQxNyAxNjUsNDE4IDE2Niw0MTggMTY3LDQxOSAxNjksNDE5IDE3MCw0MjAgMTcyLDQyMCAxNzMsNDIxIDE3NCw0MjEgMTc1LDQyMiAxNzcsNDIyIDE3OCw0MjMgMTgwLDQyMyAxODEsNDI0IDE4Myw0MjQgMTg0LDQyMyAxODQsNDIwIDE4Miw0MjAgMTgxLDQxOSAxNzksNDE5IDE3OCw0MTggMTc3LDQxOCAxNzYsNDE3IDE3NCw0MTcgMTczLDQxNiAxNzEsNDE2IDE3MCw0MTUgMTY4LDQxNSAxNjcsNDE0IDE2NCw0MTQgWiBNIDIxOCwzNjkgMjIxLDM2OSAyMjMsMzcxIDIyMywzNzQgMjI0LDM3NSAyMjMsMzc2IDIyMywzNzggMjIwLDM4MSAyMTgsMzgxIDIxNSwzNzggMjE1LDM3NiAyMTQsMzc1IDIxNCwzNzQgMjE1LDM3MyAyMTUsMzcyIFogTSAxNDgsNDA3IDE0OCw0MDggMTQ3LDQwOSAxNDcsNDEyIDE0OSw0MTIgMTUwLDQxMyAxNTEsNDEzIDE1Miw0MTQgMTU0LDQxNCAxNTUsNDE1IDE1Nyw0MTUgMTU4LDQxNiAxNjAsNDE2IDE2MCw0MTUgMTYxLDQxNCAxNjEsNDEyIDE2MCw0MTIgMTU5LDQxMSAxNTgsNDExIDE1Nyw0MTAgMTU1LDQxMCAxNTQsNDA5IDE1Miw0MDkgMTUxLDQwOCAxNTAsNDA4IDE0OSw0MDcgWiBNIDEwNyw1OSAxMDgsNTkgMTEyLDYzIDExMiw2NiAxMDgsNzAgMTA2LDY4IDEwNiw2NyAxMDMsNjQgMTAzLDYyIDEwNSw2MCAxMDYsNjAgWiBNIDEwMCw0OSAxMDMsNTIgMTAzLDU1IDEwMiw1NiAxMDIsNTcgMTAxLDU4IDk5LDU4IDk3LDU2IDk3LDU1IDk1LDUzIDk1LDUyIDk3LDUwIDk5LDUwIFogTSAyOTksNDIwIDMwMCw0MjAgMzAxLDQyMSAzMDEsNDIzIDMwMiw0MjMgMzAzLDQyNCAzMDIsNDI1IDMwMiw0MjcgMzAzLDQyOCAzMDEsNDMwIDI5OSw0MzAgMjk4LDQyOSAyOTksNDI4IDMwMCw0MjggMzAwLDQyNiAyOTksNDI1IDI5Nyw0MjUgMjk2LDQyNiAyOTUsNDI2IDI5NCw0MjUgMjk2LDQyMyAyOTgsNDIzIDI5OCw0MjEgWiBNIDIwMyw0MzYgMjA0LDQzNSAyMDgsNDM1IDIwOSw0MzYgMjE1LDQzNiAyMTYsNDM3IDIxNCw0MzkgMjA5LDQzOSAyMDgsNDM4IDIwNCw0MzggMjAzLDQzNyBaIE0gMTY2LDQyNyAxNjcsNDI2IDE2OSw0MjYgMTcwLDQyNyAxNzIsNDI3IDE3NCw0MjkgMTc0LDQzMCAxNzMsNDMxIDE3Miw0MzEgMTcxLDQzMCAxNzAsNDMwIDE2OSw0MjkgMTY3LDQyOSAxNjYsNDI4IFogTSAzMTMsNDExIDMxNCw0MTIgMzE0LDQxMyAzMTMsNDE0IDMxMiw0MTQgMzExLDQxNSAzMTEsNDE3IDMxMCw0MTggMzA5LDQxNyAzMDksNDE1IDMwNyw0MTMgMzA4LDQxMiAzMTIsNDEyIFogTSAyMDMsNDU1IDIwNCw0NTQgMjA1LDQ1NSAyMTAsNDU1IDIxMSw0NTYgMjExLDQ1NyAyMTAsNDU4IDIwNiw0NTggMjA1LDQ1NyAyMDQsNDU3IDIwMyw0NTYgWiBNIDMxNSw0MTYgMzE2LDQxNyAzMTQsNDE5IDMxMyw0MTkgMzEzLDQyMSAzMTIsNDIyIDMxMSw0MjIgMzEwLDQyMSAzMTAsNDE4IDMxMSw0MTcgMzEzLDQxNyAzMTQsNDE2IFogTSAzMTgsNDIyIDMxOCw0MjMgMzE3LDQyNCAzMTYsNDI0IDMxNSw0MjUgMzEzLDQyNSAzMTIsNDI2IDMxMSw0MjUgMzExLDQyNCAzMTMsNDIyIDMxNSw0MjIgMzE2LDQyMSAzMTcsNDIxIFogTSAxMDYsNDEyIDEwNyw0MTEgMTA4LDQxMSAxMTAsNDEzIDExMSw0MTMgMTE0LDQxNiAxMTMsNDE3IDExMiw0MTcgMTEwLDQxNSAxMDksNDE1IFogTSAyNTMsNDMxIDI1NSw0MjkgMjU3LDQyOSAyNTgsNDMwIDI1OCw0MzIgMjU3LDQzMyAyNTUsNDMzIFogTSAxNTgsNDQ0IDE1OSw0NDUgMTYwLDQ0NSAxNjEsNDQ2IDE2MCw0NDcgMTYwLDQ0OCAxNTksNDQ5IDE1Nyw0NDcgMTU3LDQ0NSBaIE0gMTU5LDQ0MCAxNjEsNDM4IDE2Myw0MzggMTY0LDQzOSAxNjMsNDQwIDE2Myw0NDEgMTYyLDQ0MiAxNjEsNDQxIDE2MCw0NDEgWiBNIDE2Nyw0NDMgMTY5LDQ0MSAxNzAsNDQxIDE3MSw0NDIgMTcxLDQ0NCAxNzAsNDQ1IDE2OSw0NDUgWiBNIDE2NCw0NTAgMTY2LDQ0OCAxNjgsNDQ4IDE2OSw0NDkgMTY3LDQ1MSAxNjUsNDUxIFogTSAzMDUsNDI3IDMwOCw0MjQgMzEwLDQyNiAzMDksNDI3IDMwOCw0MjcgMzA3LDQyOCAzMDYsNDI4IFogTSAzMDIsNDE5IDMwNCw0MTcgMzA2LDQxNyAzMDcsNDE4IDMwNSw0MjAgMzAzLDQyMCBaIE0gMjkyLDQyMCAyOTQsNDE4IDI5Niw0MTggMjk3LDQxOSAyOTYsNDIwIDI5NSw0MjAgMjk0LDQyMSAyOTMsNDIxIFogTSAxMDMsNDA5IDEwNCw0MDggMTA3LDQxMSAxMDYsNDEyIDEwNSw0MTIgMTAzLDQxMCBaIE0gMTE5LDQwNyAxMjAsNDA2IDEyMSw0MDYgMTIzLDQwOCAxMjIsNDA5IDEyMSw0MDkgWiBNIDEyMSw0MDIgMTIyLDQwMSAxMjMsNDAxIDEyNSw0MDMgMTI0LDQwNCAxMjMsNDA0IFogTSAxMTgsNDAwIDExOSwzOTkgMTIwLDM5OSAxMjIsNDAxIDEyMSw0MDIgMTIwLDQwMiBaIE0gMTU0LDQzNSAxNTUsNDM2IDE1NSw0MzggMTU0LDQzOSAxNTMsNDM4IDE1Myw0MzYgWiBNIDE1MCw0MjkgMTUxLDQzMCAxNTEsNDMyIDE1MCw0MzMgMTQ5LDQzMiAxNDksNDMwIFogTSAxMTMsNDE3IDExNCw0MTYgMTE1LDQxNiAxMTYsNDE3IDExNiw0MTggMTE1LDQxOSBaIE0gMTQ3LDQzNiAxNDgsNDM1IDE0OSw0MzYgMTQ5LDQzNyAxNDgsNDM4IDE0Nyw0MzcgWiBNIDE1NCw0MzQgMTU1LDQzMyAxNTYsNDM0IDE1Niw0MzUgMTU1LDQzNiAxNTQsNDM1IFogTSAxNDEsNDM0IDE0Miw0MzMgMTQzLDQzNCAxNDMsNDM1IDE0Miw0MzYgMTQxLDQzNSBaIE0gMTQ4LDQzMyAxNDksNDMyIDE1MCw0MzMgMTUwLDQzNCAxNDksNDM1IDE0OCw0MzQgWiBNIDE0Miw0MzEgMTQzLDQzMCAxNDQsNDMxIDE0NCw0MzIgMTQzLDQzMyAxNDIsNDMyIFogTSAxNDMsNDI5IDE0NCw0MjggMTQ1LDQyOSAxNDUsNDMwIDE0NCw0MzEgMTQzLDQzMCBaIE0gMTUwLDQyOCAxNTEsNDI3IDE1Miw0MjggMTUyLDQyOSAxNTEsNDMwIDE1MCw0MjkgWiBNIDE0NCw0MjYgMTQ1LDQyNSAxNDYsNDI2IDE0Niw0MjcgMTQ1LDQyOCAxNDQsNDI3IFogTSAyOTksNDM1IDMwMCw0MzQgMzAxLDQzNCAzMDIsNDM1IDMwMSw0MzYgMzAwLDQzNiBaIE0gMzAyLDQzNCAzMDMsNDMzIDMwNCw0MzMgMzA1LDQzNCAzMDQsNDM1IDMwMyw0MzUgWiBNIDMwNyw0MzIgMzA4LDQzMSAzMDksNDMxIDMxMCw0MzIgMzA5LDQzMyAzMDgsNDMzIFogTSAzMTIsNDMwIDMxMyw0MjkgMzE0LDQyOSAzMTUsNDMwIDMxNCw0MzEgMzEzLDQzMSBaIE0gMzE1LDQyOSAzMTYsNDI4IDMxNyw0MjggMzE4LDQyOSAzMTcsNDMwIDMxNiw0MzAgWiBNIDI5Nyw0MTYgMjk4LDQxNSAyOTksNDE1IDMwMCw0MTYgMjk5LDQxNyAyOTgsNDE3IFogTSAxMjMsNDEwIDEyNCw0MDkgMTI1LDQwOSAxMjYsNDEwIDEyNSw0MTEgMTI0LDQxMSBaIE0gMTEwLDQwOCAxMTEsNDA3IDExMiw0MDcgMTEzLDQwOCAxMTIsNDA5IDExMSw0MDkgWiBNIDEwNyw0MDYgMTA4LDQwNSAxMDksNDA1IDExMCw0MDYgMTA5LDQwNyAxMDgsNDA3IFogTSAxMDQsNDA0IDEwNSw0MDMgMTA2LDQwMyAxMDcsNDA0IDEwNiw0MDUgMTA1LDQwNSBaIE0gMTEwLDQwMSAxMTEsNDAwIDExMiw0MDAgMTEzLDQwMSAxMTIsNDAyIDExMSw0MDIgWiBNIDEwNywzOTkgMTA4LDM5OCAxMDksMzk4IDExMCwzOTkgMTA5LDQwMCAxMDgsNDAwIFogTSAxMTUsMzk4IDExNiwzOTcgMTE3LDM5NyAxMTgsMzk4IDExNywzOTkgMTE2LDM5OSBaIE0gMTE3LDM5MyAxMTgsMzkyIDExOSwzOTIgMTIwLDM5MyAxMTksMzk0IDExOCwzOTQgWiBNIDE0Niw0MzkgMTQ3LDQzOCAxNDgsNDM5IDE0Nyw0NDAgWiBNIDMwNSw0MzMgMzA2LDQzMiAzMDcsNDMzIDMwNiw0MzQgWiBNIDMxMCw0MzEgMzExLDQzMCAzMTIsNDMxIDMxMSw0MzIgWiBNIDI5Nyw0MzAgMjk4LDQyOSAyOTksNDMwIDI5OCw0MzEgWiBNIDI5Nyw0MjAgMjk4LDQxOSAyOTksNDIwIDI5OCw0MjEgWiBNIDExNSw0MjUgMTE2LDQyNCAxMTcsNDI1IDExNiw0MjYgWiBNIDEyMiw0MTYgMTIzLDQxNSAxMjQsNDE2IDEyMyw0MTcgWiBNIDEyMSw0MTUgMTIyLDQxNCAxMjMsNDE1IDEyMiw0MTYgWiBNIDExOSw0MTQgMTIwLDQxMyAxMjEsNDE0IDEyMCw0MTUgWiBNIDExOCw0MTMgMTE5LDQxMiAxMjAsNDEzIDExOSw0MTQgWiBNIDExNiw0MTIgMTE3LDQxMSAxMTgsNDEyIDExNyw0MTMgWiBNIDExNSw0MTEgMTE2LDQxMCAxMTcsNDExIDExNiw0MTIgWiBNIDExMyw0MTAgMTE0LDQwOSAxMTUsNDEwIDExNCw0MTEgWiBNIDEyMiw0MDkgMTIzLDQwOCAxMjQsNDA5IDEyMyw0MTAgWiBNIDExMiw0MDkgMTEzLDQwOCAxMTQsNDA5IDExMyw0MTAgWiBNIDEwOSw0MDcgMTEwLDQwNiAxMTEsNDA3IDExMCw0MDggWiBNIDEwNiw0MDUgMTA3LDQwNCAxMDgsNDA1IDEwNyw0MDYgWiBNIDEwMyw0MDMgMTA0LDQwMiAxMDUsNDAzIDEwNCw0MDQgWiBNIDExMiw0MDIgMTEzLDQwMSAxMTQsNDAyIDExMyw0MDMgWiBNIDEwOSw0MDAgMTEwLDM5OSAxMTEsNDAwIDExMCw0MDEgWiBNIDEyNiwzOTkgMTI3LDM5OCAxMjgsMzk5IDEyNyw0MDAgWiBNIDExNywzOTkgMTE4LDM5OCAxMTksMzk5IDExOCw0MDAgWiBNIDEyNSwzOTggMTI2LDM5NyAxMjcsMzk4IDEyNiwzOTkgWiBNIDEwNiwzOTggMTA3LDM5NyAxMDgsMzk4IDEwNywzOTkgWiBNIDEyMywzOTcgMTI0LDM5NiAxMjUsMzk3IDEyNCwzOTggWiBNIDExNCwzOTcgMTE1LDM5NiAxMTYsMzk3IDExNSwzOTggWiBNIDEyMiwzOTYgMTIzLDM5NSAxMjQsMzk2IDEyMywzOTcgWiBNIDExMywzOTYgMTE0LDM5NSAxMTUsMzk2IDExNCwzOTcgWiBNIDEyMCwzOTUgMTIxLDM5NCAxMjIsMzk1IDEyMSwzOTYgWiBNIDExOSwzOTQgMTIwLDM5MyAxMjEsMzk0IDEyMCwzOTUgWiBNIDExNiwzOTIgMTE3LDM5MSAxMTgsMzkyIDExNywzOTMgWiBNIDM0NCw0MjEgMzQ1LDQyMCAzNDYsNDIxIDM0NSw0MjIgWiBNIDM0OCw0MTUgMzQ5LDQxNCAzNTAsNDE1IDM0OSw0MTYgWiBNIDM1NiwzOTIgMzU3LDM5MSAzNTgsMzkyIDM1NywzOTMgWiBNIDM4NiwzODMgMzg3LDM4MiAzODgsMzgzIDM4NywzODQgWiIgZmlsbD0iIzBCNjNBNyIgZmlsbC1ydWxlPSJldmVub2RkIiBjbGlwLXJ1bGU9ImV2ZW5vZGQiLz48L3N2Zz4="
LOGO_DATA_URI = f"data:image/png;base64,{LOGO_PNG_BASE64}"
LOGO_IMAGE = "🏫"

# 기본 설정
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="경복고등학교 북악제",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FESTIVAL_NAME = "북악제"
FESTIVAL_SLOGAN = "빛나는 우리, 하나의 이야기"
FESTIVAL_DATE = date(2026, 10, 30)
FESTIVAL_DATETIME = datetime.combine(FESTIVAL_DATE, dtime(0, 0, 0))
FESTIVAL_TZ_OFFSET = "+09:00"

FAKE_EMAIL_DOMAIN = "bukakje.internal"

NOTICES_CACHE_TTL = 20
BOOTHS_CACHE_TTL = 30
PROGRAMS_CACHE_TTL = 30
SCHEDULE_CACHE_TTL = 30

# ----------------------------------------------------------------------
# Supabase 클라이언트
# ----------------------------------------------------------------------
try:
    from supabase import create_client, Client
except ImportError:
    st.error(
        "`supabase` 패키지가 설치되어 있지 않습니다.\n\n"
        "터미널에서 `pip install supabase` 를 실행한 뒤 다시 시작해주세요."
    )
    st.stop()

try:
    from streamlit_cookies_manager import EncryptedCookieManager
except ImportError:
    st.error(
        "`streamlit-cookies-manager` 패키지가 설치되어 있지 않습니다.\n\n"
        "터미널에서 `pip install streamlit-cookies-manager` 를 실행한 뒤 다시 시작해주세요."
    )
    st.stop()


def _debug_secret_paths() -> str:
    candidates = []
    try:
        candidates.append(Path(__file__).resolve().parent / ".streamlit" / "secrets.toml")
    except Exception:
        pass
    candidates.append(Path.home() / ".streamlit" / "secrets.toml")

    lines = []
    for p in candidates:
        if p.exists():
            lines.append(f"- `{p}` → 존재함 ✅")
        else:
            parent = p.parent
            if parent.exists():
                found = [f.name for f in parent.iterdir()]
                hint = f" (이 폴더 안 실제 파일들: {found})" if found else " (이 폴더는 비어있음)"
            else:
                hint = " (이 폴더 자체가 없음)"
            lines.append(f"- `{p}` → 없음 ❌{hint}")
    return "\n".join(lines)


def _get_secret(key: str, required: bool = True, default=None):
    try:
        val = st.secrets.get(key)
    except Exception:
        val = None
        if required:
            st.error(
                "`secrets.toml` 파일을 찾을 수 없습니다.\n\n"
                "다음 경로들을 확인해봤습니다.\n\n"
                f"{_debug_secret_paths()}\n\n"
                "파일이 아예 없다면 스크립트가 있는 폴더 밑에 `.streamlit` 폴더를 만들고 "
                "그 안에 `secrets.toml` 파일을 아래 형식으로 만들어주세요.\n\n"
                "```\n"
                "SUPABASE_URL = \"https://xxxxxxxxxxxx.supabase.co\"\n"
                "SUPABASE_ANON_KEY = \"anon 키\"\n"
                "SUPABASE_SERVICE_KEY = \"service_role 키 (선택)\"\n"
                "```"
            )
            st.stop()
    if required and not val:
        st.error(
            f"`.streamlit/secrets.toml` 에 `{key}` 값이 설정되어 있지 않습니다.\n\n"
            "함께 받은 `supabase_setup.sql` 안내와 secrets.toml 예시를 참고해 설정해주세요."
        )
        st.stop()
    if not val:
        return default
    return val


SUPABASE_URL = _get_secret("SUPABASE_URL")
SUPABASE_ANON_KEY = _get_secret("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = _get_secret("SUPABASE_SERVICE_KEY", required=False)

COOKIE_PASSWORD = _get_secret(
    "COOKIE_PASSWORD", required=False,
    default="bukakje-insecure-default-change-me-in-secrets-toml",
)
if COOKIE_PASSWORD == "bukakje-insecure-default-change-me-in-secrets-toml":
    st.warning(
        "⚠️ `secrets.toml` 에 `COOKIE_PASSWORD` 가 설정되어 있지 않아 "
        "임시 기본값을 사용합니다. 서버를 재시작하면 로그인 유지 쿠키가 무효화될 수 있으니 "
        "`COOKIE_PASSWORD = \"아무 긴 임의 문자열\"` 을 secrets.toml에 추가해주세요.",
        icon="⚠️",
    )


def get_user_client() -> "Client":
    if "sb_client" not in st.session_state:
        st.session_state.sb_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return st.session_state.sb_client


@st.cache_resource
def get_admin_client():
    if not SUPABASE_SERVICE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def student_email(student_no: str) -> str:
    return f"student-{student_no.strip()}@{FAKE_EMAIL_DOMAIN}"


def staff_login_email(username: str) -> str:
    return f"staffid-{username.strip()}@{FAKE_EMAIL_DOMAIN}"


# ----------------------------------------------------------------------
# 쿠키 매니저 초기화 (로그인 유지용)
# ----------------------------------------------------------------------
cookies = EncryptedCookieManager(prefix="bukakje_", password=COOKIE_PASSWORD)
if not cookies.ready():
    st.stop()


def save_auth_cookies(session):
    if session is None:
        return
    try:
        cookies["sb_access_token"] = session.access_token or ""
        cookies["sb_refresh_token"] = session.refresh_token or ""
        cookies.save()
    except Exception:
        pass


def save_guest_pass_name(name: str):
    """비회원 이름을 현재 세션과 이 브라우저 쿠키에 저장합니다."""
    clean_name = (name or "").strip()[:20]
    st.session_state["guest_pass_name"] = clean_name
    try:
        cookies["guest_pass_name"] = clean_name
        cookies.save()
    except Exception:
        pass
    return clean_name


def get_guest_pass_name() -> str:
    """세션 이름을 우선 사용하고, 새 세션이면 브라우저 쿠키에서 복원합니다."""
    if "guest_pass_name" in st.session_state:
        return st.session_state["guest_pass_name"] or ""
    try:
        saved = cookies.get("guest_pass_name") or ""
    except Exception:
        saved = ""
    st.session_state["guest_pass_name"] = saved
    return saved

def clear_auth_cookies():
    try:
        cookies["sb_access_token"] = ""
        cookies["sb_refresh_token"] = ""
        cookies.save()
    except Exception:
        pass


def try_restore_session_from_cookies():
    if st.session_state.get("current_user_id"):
        return

    access_token = cookies.get("sb_access_token")
    refresh_token = cookies.get("sb_refresh_token")
    if not access_token or not refresh_token:
        return

    client = get_user_client()
    try:
        client.auth.set_session(access_token, refresh_token)
        user_res = client.auth.get_user()
    except Exception:
        clear_auth_cookies()
        return

    if user_res and user_res.user:
        st.session_state.current_user_id = user_res.user.id
        st.session_state.profile_cache = None
    else:
        clear_auth_cookies()


# ----------------------------------------------------------------------
# 디자인 토큰
# ----------------------------------------------------------------------
NAVY = "#0F1F3D"
NAVY_2 = "#16294F"
ORANGE = "#F2994A"
ORANGE_DARK = "#E07B2E"
BLUE_PILL = "#2F5D9F"
GREEN = "#2E9E5B"
BG = "#F5F6FA"
CARD = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Nanum+Myeongjo:wght@700;800&display=swap');

html, body, [class*="css"]  {{
    font-family: 'Noto Sans KR', sans-serif;
}}
.stApp {{
    background: {BG};
}}
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header[data-testid="stHeader"] {{display: none;}}

.block-container {{
    padding-top: 4.4rem !important;
    padding-bottom: 2rem;
}}

.bk-drawer-checkbox {{
    display: none;
}}

.bk-topbar {{
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3.4rem;
    background: {NAVY};
    color: white;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 18px;
    z-index: 1000000;
    box-shadow: 0 2px 10px rgba(0,0,0,0.15);
}}
.bk-brand {{
    font-weight: 900;
    font-size: 17px;
    color: white !important;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.bk-brand-logo {{
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: white;
    object-fit: contain;
    padding: 2px;
}}
.bk-brand:hover {{
    color: {ORANGE} !important;
}}
.bk-hamburger {{
    cursor: pointer;
    font-size: 24px;
    line-height: 1;
    background: {ORANGE};
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    user-select: none;
}}

.bk-backdrop {{
    position: fixed;
    inset: 0;
    background: rgba(10,15,30,0.55);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s ease;
    z-index: 1000001;
    display: block;
    cursor: pointer;
}}

.bk-drawer {{
    position: fixed;
    top: 0; right: 0;
    height: 100vh;
    width: min(300px, 82vw);
    background: {NAVY};
    transform: translateX(100%);
    transition: transform 0.3s ease;
    z-index: 1000002;
    padding: 18px 16px;
    overflow-y: auto;
    box-shadow: -8px 0 24px rgba(0,0,0,0.3);
}}
.bk-drawer-head {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    color: white;
    font-weight: 900;
    font-size: 16px;
    margin-bottom: 14px;
}}
.bk-drawer-close {{
    cursor: pointer;
    font-size: 18px;
    color: white;
    background: rgba(255,255,255,0.12);
    width: 32px; height: 32px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
}}
.bk-drawer-link {{
    display: block;
    color: #EDEFF5 !important;
    text-decoration: none !important;
    font-weight: 600;
    font-size: 15px;
    padding: 12px 10px;
    border-radius: 10px;
    margin-bottom: 4px;
}}
.bk-drawer-link:hover {{
    background: rgba(255,255,255,0.10);
    color: {ORANGE} !important;
}}
.bk-drawer-link.bk-active {{
    background: {ORANGE};
    color: white !important;
}}
.bk-drawer-divider {{
    border: none;
    border-top: 1px solid rgba(255,255,255,0.15);
    margin: 12px 0;
}}
.bk-drawer-user {{
    color: #C9D2E8;
    font-size: 13px;
    padding: 0 10px 8px 10px;
}}

.bk-drawer-checkbox:checked ~ .bk-backdrop {{
    opacity: 1;
    pointer-events: auto;
}}
.bk-drawer-checkbox:checked ~ .bk-drawer {{
    transform: translateX(0);
}}

.bk-card {{
    background: {CARD};
    border-radius: 16px;
    padding: 22px;
    box-shadow: 0 2px 14px rgba(15,31,61,0.08);
    height: 100%;
}}
.bk-card h4 {{
    margin: 0 0 12px 0;
    color: {NAVY};
}}
.bk-badge-new {{
    background: {ORANGE};
    color: white;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: 8px;
}}
.bk-pill {{
    display: inline-block;
    background: {NAVY};
    color: white;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
}}
.bk-chip {{
    display: inline-block;
    background: #EEF1F8;
    color: {NAVY};
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    margin-right: 6px;
}}

.bk-card-btn {{
    display: inline-block;
    margin-top: 10px;
    color: {ORANGE_DARK} !important;
    font-weight: 700;
    font-size: 14px;
    text-decoration: none !important;
}}
.bk-card-btn:hover {{
    text-decoration: underline !important;
}}

.bk-hero {{
    position: relative;
    border-radius: 20px;
    padding: 46px 40px;
    min-height: 300px;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: center;
    background:
      radial-gradient(circle at 10% 20%, rgba(242,153,74,0.55) 0px, transparent 3px),
      radial-gradient(circle at 25% 15%, rgba(242,153,74,0.55) 0px, transparent 3px),
      radial-gradient(circle at 40% 25%, rgba(242,153,74,0.55) 0px, transparent 3px),
      radial-gradient(circle at 55% 12%, rgba(242,153,74,0.55) 0px, transparent 3px),
      radial-gradient(circle at 70% 22%, rgba(242,153,74,0.55) 0px, transparent 3px),
      radial-gradient(circle at 85% 15%, rgba(242,153,74,0.55) 0px, transparent 3px),
      radial-gradient(circle at 95% 25%, rgba(242,153,74,0.55) 0px, transparent 3px),
      linear-gradient(180deg, {NAVY} 0%, {NAVY_2} 60%, #0B1730 100%);
    color: white;
    overflow: hidden;
}}
.bk-hero .eyebrow {{
    font-size: 13px;
    color: #C9D2E8;
    font-weight: 600;
    letter-spacing: 1px;
}}
.bk-hero h1 {{
    font-size: 64px;
    font-weight: 900;
    margin: 4px 0 6px 0;
    line-height: 1.05;
    color: white !important;
}}
.bk-hero .slogan {{
    font-size: 18px;
    color: #E7EBF6;
    margin-bottom: 18px;
}}
.bk-hero .meta {{
    font-size: 14px;
    color: #D8DEEE;
}}
.bk-dday-box {{
    background: white;
    border-radius: 16px;
    padding: 18px 22px;
    text-align: center;
    color: {NAVY};
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}}
.bk-dday-box .num {{
    font-size: 36px;
    font-weight: 900;
    color: {ORANGE_DARK};
}}

.bk-iconmenu .stButton>button {{
    width: 100%;
    border: none;
    background: white;
    border-radius: 14px;
    padding: 16px 4px;
    box-shadow: 0 2px 10px rgba(15,31,61,0.07);
    font-weight: 700;
    color: {NAVY};
}}
.bk-iconmenu .stButton>button:hover {{
    background: #EEF1F8;
    color: {ORANGE_DARK};
}}

div.stButton>button {{
    border-radius: 10px;
}}

.bk-section-title {{
    font-size: 22px;
    font-weight: 900;
    color: {NAVY};
    margin: 30px 0 14px 0;
}}
.bk-footer {{
    margin-top: 40px;
    padding: 24px;
    background: {NAVY};
    color: #D8DEEE;
    border-radius: 16px;
    font-size: 14px;
}}
hr {{border-color: #E5E7EF;}}

.bk-fab {{
    position: fixed;
    right: 22px;
    bottom: 22px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: {ORANGE};
    color: white !important;
    font-size: 30px;
    font-weight: 900;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    text-decoration: none !important;
    box-shadow: 0 6px 18px rgba(224,123,46,0.45);
    z-index: 999998;
}}
.bk-fab:hover {{
    background: {ORANGE_DARK};
}}

.bk-media-wrap {{
    position: relative;
    width: 100%;
}}
.bk-media-icon-badge {{
    position: absolute;
    right: 8px;
    bottom: 8px;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}}

/* ---------------- 디지털 방문증 (프리미엄 티켓형) ---------------- */
.bk-pass-wrap {{ width:100%; max-width:520px; margin:0 auto 20px; }}
.bk-pass-card {{ position:relative; overflow:hidden; border-radius:24px; background:#fff; border:1px solid #D9DEE8; box-shadow:0 18px 45px rgba(15,31,61,.16); }}
.bk-pass-top {{ position:relative; padding:30px 28px 25px; text-align:center; background:linear-gradient(180deg,#fff 0%,#F7F9FC 100%); border-bottom:1px solid #E1E5EC; }}
.bk-pass-top::before {{ content:""; position:absolute; inset:10px; border:1px solid rgba(11,99,167,.16); border-radius:16px; pointer-events:none; }}
.bk-pass-top-label {{ position:relative; z-index:2; font-size:10px; font-weight:800; letter-spacing:2px; color:#7A8495; margin-bottom:10px; }}
.bk-pass-emblem {{ width:136px; height:136px; object-fit:contain; display:block; margin:0 auto 8px; position:relative; z-index:2; }}
.bk-pass-title-main {{ position:relative; z-index:2; font-family:'Nanum Myeongjo','Noto Sans KR',serif; font-size:44px; line-height:1; font-weight:900; letter-spacing:8px; text-indent:8px; color:#0B63A7; margin:3px 0 10px; }}
.bk-pass-subtitle {{ position:relative; z-index:2; font-size:11px; font-weight:800; letter-spacing:2px; color:#667085; }}
.bk-pass-rule {{ position:relative; z-index:2; display:flex; align-items:center; gap:9px; width:75%; margin:15px auto 0; color:#C59642; }}
.bk-pass-rule span {{ flex:1; height:1px; background:#D9C28D; }} .bk-pass-rule b {{ font-size:12px; }}
.bk-pass-perforation {{ position:relative; height:1px; border-top:2px dashed #D9DEE8; margin:0 20px; }}
.bk-pass-perforation::before,.bk-pass-perforation::after {{ content:""; position:absolute; top:-14px; width:27px; height:27px; background:{BG}; border-radius:50%; }}
.bk-pass-perforation::before {{ left:-34px; }} .bk-pass-perforation::after {{ right:-34px; }}
.bk-pass-bottom {{ display:grid; grid-template-columns:1fr 1px 92px; gap:18px; padding:24px 27px 22px; background:#fff; }}
.bk-pass-bottom-left {{ min-width:0; }} .bk-pass-bl-title {{ color:#0B63A7; font-size:15px; font-weight:900; letter-spacing:1px; margin-bottom:14px; }}
.bk-pass-meta-row {{ color:#475467; font-size:13px; line-height:1.55; margin-bottom:6px; }}
.bk-pass-name-label {{ margin-top:13px; font-size:10px; font-weight:900; letter-spacing:1.5px; color:#98A2B3; }}
.bk-pass-name-box {{ margin:4px 0 10px; padding:5px 0 8px; border-bottom:2px solid #0B63A7; font-size:20px; font-weight:900; color:#0F1F3D; word-break:keep-all; }}
.bk-pass-name-box.empty {{ color:#98A2B3; font-size:15px; font-weight:600; }}
.bk-pass-name-type {{ margin-left:8px; padding:3px 7px; border-radius:999px; background:#EEF5FB; color:#0B63A7; font-size:10px; font-weight:800; vertical-align:middle; }}
.date-row {{ margin-top:9px; }} .bk-pass-vdivider {{ width:1px; background:repeating-linear-gradient(to bottom,#D9DEE8 0,#D9DEE8 5px,transparent 5px,transparent 10px); }}
.bk-pass-bottom-right {{ display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; }}
.bk-pass-date-label {{ font-size:10px; font-weight:900; letter-spacing:2px; color:#98A2B3; }} .bk-pass-date-num {{ color:#0B63A7; font-size:42px; font-weight:900; line-height:1.05; }}
.bk-pass-weekday-eng {{ margin-top:3px; color:#667085; font-size:11px; font-weight:800; letter-spacing:2px; }}
.bk-pass-footer {{ display:flex; justify-content:space-between; gap:10px; padding:11px 22px; background:#0B63A7; color:#fff; font-size:9px; font-weight:900; letter-spacing:1.5px; }}
.bk-pass-register {{ margin-top:14px; }}
@media (max-width:600px) {{ .bk-pass-wrap {{max-width:100%;}} .bk-pass-top {{padding:24px 18px 21px;}} .bk-pass-emblem {{width:112px;height:112px;}} .bk-pass-title-main {{font-size:36px;letter-spacing:6px;text-indent:6px;}} .bk-pass-bottom {{grid-template-columns:1fr 1px 72px;gap:12px;padding:20px 18px;}} .bk-pass-date-num {{font-size:34px;}} }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# 세션 상태 초기화
#  - 프로그램(programs)/시간표(schedule)는 이제 Supabase 테이블로 관리하므로
#    더 이상 세션 상태에 기본값을 넣지 않습니다.
# ----------------------------------------------------------------------
def init_state():
    ss = st.session_state

    if "page" not in ss:
        ss.page = "메인"

    if "current_user_id" not in ss:
        ss.current_user_id = None

    if "profile_cache" not in ss:
        ss.profile_cache = None

    if "student_step" not in ss:
        ss.student_step = "check"
    if "staff_step" not in ss:
        ss.staff_step = "check"

    if "site_info" not in ss:
        ss.site_info = {
            "address": "서울특별시 종로구 자하문로 17길 33 (경복고등학교)",
            "subway": "3호선 경복궁역 3번 출구 도보 15분",
            "bus": "간선/지선버스 다수 노선 '경복고등학교' 정류장 하차",
            "walk": "경복궁역에서 도보 약 15분",
            "phone": "02-123-4567 (행사 운영본부)",
            "email": "bukakje@kboye.kr",
            "hours": "평일 09:00 ~ 17:00",
        }


init_state()
ss = st.session_state

try_restore_session_from_cookies()


# ----------------------------------------------------------------------
# 헬퍼
# ----------------------------------------------------------------------
def go(page_name: str):
    ss.page = page_name


def reset_login_steps():
    ss.student_step = "check"
    ss.staff_step = "check"
    for k in ("pending_student_no", "pending_student_name", "pending_student_email",
              "pending_staff_code", "pending_staff_name"):
        ss.pop(k, None)


def current_user():
    ss.last_profile_error = None
    uid = ss.get("current_user_id")
    if not uid:
        return None
    cache = ss.get("profile_cache")
    if cache and cache.get("id") == uid:
        return cache
    try:
        client = get_user_client()
        res = client.table("profiles").select("*").eq("id", uid).execute()
    except Exception as e:
        ss.last_profile_error = f"프로필 조회 중 오류: {e}"
        return None
    if res.data:
        ss.profile_cache = res.data[0]
        return ss.profile_cache
    ss.last_profile_error = (
        "로그인 세션은 있지만 profiles 테이블에서 해당 사용자 행을 찾지 못했습니다. "
        "(회원가입 시 프로필 insert가 실패했거나, RLS 정책이 select를 막고 있을 수 있습니다.)"
    )
    return None


def is_admin():
    u = current_user()
    return bool(u and u.get("is_admin"))


# ----------------------------------------------------------------------
# DB 오류 처리 헬퍼
# ----------------------------------------------------------------------
def _friendly_db_error(e: Exception) -> str:
    msg = str(e)
    if "infinite recursion detected in policy" in msg or "42P17" in msg:
        return (
            "Supabase의 RLS(행 수준 보안) 정책이 자기 자신을 참조해서 "
            "무한 재귀에 빠졌습니다 (42P17). Supabase 대시보드 SQL Editor에서 "
            "제공받은 RLS 수정 스크립트를 실행한 뒤 다시 시도해주세요."
        )
    if "relation" in msg and "does not exist" in msg:
        return (
            "필요한 테이블이 아직 없습니다. 이 파일 상단 주석의 SQL을 "
            "Supabase SQL Editor에서 먼저 실행해주세요.\n\n"
            f"(원본 오류: {msg})"
        )
    return f"데이터베이스 오류가 발생했습니다: {msg}"


def _write_client():
    admin_client = get_admin_client()
    return admin_client if admin_client is not None else get_user_client()


# ----------------------------------------------------------------------
# 공지사항 / 부스 — Supabase 연동
# ----------------------------------------------------------------------
@st.cache_data(ttl=NOTICES_CACHE_TTL)
def fetch_notices(viewer_scope="public"):
    client = get_user_client()
    is_member = viewer_scope == "member"
    try:
        res = client.table("notices").select("*").order("created_at", desc=True).execute()
    except Exception as e:
        st.error(_friendly_db_error(e))
        return []
    result = []
    for row in (res.data or []):
        visibility = row.get("visibility") or "all"
        if visibility == "members" and not is_member:
            continue
        created = row.get("created_at") or ""
        result.append({
            "id": row["id"],
            "title": row.get("title") or "",
            "content": row.get("content") or "",
            "date": created[:10] if created else "",
            "new": bool(row.get("is_new")),
            "visibility": visibility,
        })
    return result


def add_notice(title: str, content: str, is_new: bool, visibility: str = "all"):
    try:
        _write_client().table("notices").insert({
            "title": title, "content": content, "is_new": is_new,
            "visibility": visibility,
        }).execute()
        fetch_notices.clear()
        return True, "공지사항이 등록되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def update_notice(notice_id, title: str, content: str, is_new: bool, visibility: str = "all"):
    try:
        _write_client().table("notices").update({
            "title": title, "content": content, "is_new": is_new,
            "visibility": visibility,
        }).eq("id", notice_id).execute()
        fetch_notices.clear()
        return True, "공지사항이 수정되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def delete_notice(notice_id):
    try:
        _write_client().table("notices").delete().eq("id", notice_id).execute()
        fetch_notices.clear()
        return True, "공지사항이 삭제되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


@st.cache_data(ttl=FAQ_CACHE_TTL if "FAQ_CACHE_TTL" in globals() else 30)
def fetch_faqs():
    client = get_user_client()
    try:
        res = client.table("faqs").select("*").order("created_at", desc=True).execute()
        return [{"id": r["id"], "question": r.get("question") or "",
                 "answer": r.get("answer") or ""} for r in (res.data or [])]
    except Exception as e:
        st.error(_friendly_db_error(e))
        return []


def add_faq(question: str, answer: str):
    try:
        _write_client().table("faqs").insert({"question": question, "answer": answer}).execute()
        fetch_faqs.clear()
        return True, "FAQ가 등록되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def update_faq(faq_id, question: str, answer: str):
    try:
        _write_client().table("faqs").update({"question": question, "answer": answer}).eq("id", faq_id).execute()
        fetch_faqs.clear()
        return True, "FAQ가 수정되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def delete_faq(faq_id):
    try:
        _write_client().table("faqs").delete().eq("id", faq_id).execute()
        fetch_faqs.clear()
        return True, "FAQ가 삭제되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


@st.cache_data(ttl=BOOTHS_CACHE_TTL)
def fetch_booths():
    client = get_user_client()
    try:
        res = client.table("booths").select("*").order("created_at", desc=True).execute()
    except Exception as e:
        st.error(_friendly_db_error(e))
        return []
    result = []
    for row in (res.data or []):
        result.append({
            "id": row["id"],
            "name": row.get("name") or "",
            "category": row.get("category") or "",
            "place": row.get("place") or "",
            "hours": row.get("hours") or "",
            "desc": row.get("description") or "",
            "icon": row.get("icon") or "🏪",
            "image": row.get("image"),
        })
    return result


def add_booth(data: dict):
    try:
        _write_client().table("booths").insert({
            "name": data["name"], "category": data["category"], "place": data["place"],
            "hours": data["hours"], "description": data["desc"], "icon": data["icon"],
            "image": data.get("image"),
        }).execute()
        fetch_booths.clear()
        return True, "부스가 등록되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def update_booth(booth_id, data: dict):
    payload = {
        "name": data["name"], "category": data["category"], "place": data["place"],
        "hours": data["hours"], "description": data["desc"], "icon": data["icon"],
    }
    if "image" in data:
        payload["image"] = data["image"]
    try:
        _write_client().table("booths").update(payload).eq("id", booth_id).execute()
        fetch_booths.clear()
        return True, "부스 정보가 수정되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def delete_booth(booth_id):
    try:
        _write_client().table("booths").delete().eq("id", booth_id).execute()
        fetch_booths.clear()
        return True, "부스가 삭제되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


# ----------------------------------------------------------------------
# 프로그램 — Supabase 연동 (관리자 추가/수정/삭제 가능)
# ----------------------------------------------------------------------
@st.cache_data(ttl=PROGRAMS_CACHE_TTL)
def fetch_programs():
    client = get_user_client()
    try:
        res = client.table("programs").select("*").order("created_at", desc=True).execute()
    except Exception as e:
        st.error(_friendly_db_error(e))
        return []
    result = []
    for row in (res.data or []):
        result.append({
            "id": row["id"],
            "name": row.get("name") or "",
            "category": row.get("category") or "기타",
            "date": row.get("program_date") or "",
            "time": row.get("program_time") or "",
            "place": row.get("place") or "",
            "desc": row.get("description") or "",
            "icon": row.get("icon") or "🎫",
        })
    return result


def add_program(data: dict):
    try:
        _write_client().table("programs").insert({
            "name": data["name"], "category": data["category"],
            "program_date": data["date"], "program_time": data["time"],
            "place": data["place"], "description": data["desc"],
            "icon": data["icon"],
        }).execute()
        fetch_programs.clear()
        return True, "프로그램이 등록되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def update_program(program_id, data: dict):
    try:
        _write_client().table("programs").update({
            "name": data["name"], "category": data["category"],
            "program_date": data["date"], "program_time": data["time"],
            "place": data["place"], "description": data["desc"],
            "icon": data["icon"],
        }).eq("id", program_id).execute()
        fetch_programs.clear()
        return True, "프로그램이 수정되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def delete_program(program_id):
    try:
        _write_client().table("programs").delete().eq("id", program_id).execute()
        fetch_programs.clear()
        return True, "프로그램이 삭제되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


# ----------------------------------------------------------------------
# 시간표 — Supabase 연동 (관리자 추가/수정/삭제 가능)
# ----------------------------------------------------------------------
@st.cache_data(ttl=SCHEDULE_CACHE_TTL)
def fetch_schedule_flat():
    client = get_user_client()
    try:
        res = client.table("schedule").select("*").order("day").order("time").execute()
    except Exception as e:
        st.error(_friendly_db_error(e))
        return []
    result = []
    for row in (res.data or []):
        result.append({
            "id": row["id"],
            "day": row.get("day") or "",
            "time": row.get("time") or "",
            "program": row.get("program") or "",
            "place": row.get("place") or "",
        })
    return result


def fetch_schedule_by_day():
    """일자별로 묶은 dict를 반환합니다. {day: [items...]} (day 기준 오름차순 정렬)"""
    grouped = {}
    for item in fetch_schedule_flat():
        grouped.setdefault(item["day"], []).append(item)
    return dict(sorted(grouped.items()))


def add_schedule_item(data: dict):
    try:
        _write_client().table("schedule").insert({
            "day": data["day"], "time": data["time"],
            "program": data["program"], "place": data["place"],
        }).execute()
        fetch_schedule_flat.clear()
        return True, "시간표 항목이 등록되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def update_schedule_item(item_id, data: dict):
    try:
        _write_client().table("schedule").update({
            "day": data["day"], "time": data["time"],
            "program": data["program"], "place": data["place"],
        }).eq("id", item_id).execute()
        fetch_schedule_flat.clear()
        return True, "시간표 항목이 수정되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


def delete_schedule_item(item_id):
    try:
        _write_client().table("schedule").delete().eq("id", item_id).execute()
        fetch_schedule_flat.clear()
        return True, "시간표 항목이 삭제되었습니다."
    except Exception as e:
        return False, _friendly_db_error(e)


# ----------------------------------------------------------------------
# 부스 카드에 쓸 이미지 / 아이콘 영역 HTML
# ----------------------------------------------------------------------
def booth_media_html(b: dict, height: str = "150px") -> str:
    icon = b.get("icon") or "🏪"
    if b.get("image"):
        return (
            f'<div class="bk-media-wrap" style="height:{height};margin-bottom:10px;">'
            f'<div style="width:100%;height:100%;border-radius:14px;overflow:hidden;'
            f'box-shadow:0 3px 12px rgba(15,31,61,0.15);">'
            f'<img src="{b["image"]}" style="width:100%;height:100%;object-fit:cover;'
            f'display:block;">'
            f'</div>'
            f'<div class="bk-media-icon-badge">{icon}</div>'
            f'</div>'
        )
    return (
        f'<div style="width:100%;height:{height};border-radius:14px;margin-bottom:10px;'
        f'background:linear-gradient(135deg,{NAVY} 0%, {BLUE_PILL} 100%);'
        f'display:flex;align-items:center;justify-content:center;font-size:42px;">'
        f'{icon}'
        f'</div>'
    )


def days_left():
    return (FESTIVAL_DATE - date.today()).days


def render_dday_box():
    target_iso = FESTIVAL_DATETIME.strftime("%Y-%m-%dT%H:%M:%S") + FESTIVAL_TZ_OFFSET
    components.html(
        f"""
        <div style="padding:20px 0;box-sizing:border-box;">
            <div style="font-family:'Noto Sans KR',sans-serif;background:white;border-radius:20px;
                        height:260px;box-sizing:border-box;
                        display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;
                        padding:24px 22px;text-align:center;color:{NAVY};
                        box-shadow:0 8px 24px rgba(0,0,0,0.25);">
                <div>
                    <div style="font-size:13px;font-weight:700;color:{MUTED};letter-spacing:2px;">D-DAY</div>
                    <div id="bk-dday-num" style="font-size:44px;font-weight:900;color:{ORANGE_DARK};
                                font-variant-numeric:tabular-nums;letter-spacing:1px;margin-top:4px;">-</div>
                    <div id="bk-dday-sub" style="font-size:13px;color:{TEXT};margin-top:4px;">계산 중...</div>
                </div>
                <span style="display:inline-block;background:{NAVY};color:white;padding:6px 16px;
                            border-radius:20px;font-size:13px;font-weight:600;">
                    📅 {FESTIVAL_DATE.strftime('%Y.%m.%d')}
                </span>
            </div>
        </div>
        <script>
            const target = new Date("{target_iso}").getTime();
            function bkTick() {{
                const now = new Date().getTime();
                const diff = target - now;
                const numEl = document.getElementById('bk-dday-num');
                const subEl = document.getElementById('bk-dday-sub');
                if (!numEl || !subEl) return;

                if (diff <= 0) {{
                    numEl.style.fontSize = '36px';
                    numEl.innerText = '0';
                    subEl.innerText = '축제가 시작되었습니다!';
                }} else if (diff < 86400000) {{
                    const h = Math.floor(diff / (1000 * 60 * 60));
                    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                    const s = Math.floor((diff % (1000 * 60)) / 1000);
                    const pad = (n) => String(n).padStart(2, '0');
                    numEl.style.fontSize = '30px';
                    numEl.innerText = pad(h) + ':' + pad(m) + ':' + pad(s);
                    subEl.innerText = '곧 시작합니다!';
                }} else {{
                    const d = Math.ceil(diff / 86400000);
                    numEl.style.fontSize = '36px';
                    numEl.innerText = String(d);
                    subEl.innerText = d + '일 남았습니다!';
                }}
            }}
            bkTick();
            setInterval(bkTick, 1000);
        </script>
        """,
        height=300,
    )


# ---------- 학생 로그인/가입 ----------
def profile_exists_by_student_no(student_no: str):
    client = get_user_client()
    try:
        res = (
            client.table("profiles")
            .select("id,name,school_email")
            .eq("student_no", student_no)
            .execute()
        )
    except Exception as e:
        st.error(_friendly_db_error(e))
        st.stop()
    return res.data[0] if res.data else None


def send_student_otp(school_email: str):
    client = get_user_client()
    try:
        client.auth.sign_in_with_otp({
            "email": school_email,
            "options": {"should_create_user": True},
        })
    except Exception as e:
        return False, f"인증코드 발송에 실패했습니다: {e}"
    return True, "입력하신 학교 이메일로 인증코드를 보냈습니다."


def verify_student_otp(school_email: str, code: str):
    client = get_user_client()
    try:
        auth_res = client.auth.verify_otp({
            "email": school_email,
            "token": code.strip(),
            "type": "email",
        })
    except Exception:
        return False, "인증코드가 올바르지 않거나 만료되었습니다."
    if auth_res.user is None or auth_res.session is None:
        return False, "인증코드가 올바르지 않거나 만료되었습니다."
    return True, "인증되었습니다."


def finish_student_signup(student_no: str, name: str, school_email: str, password: str):
    client = get_user_client()
    try:
        update_res = client.auth.update_user({"password": password})
    except Exception as e:
        return False, f"비밀번호 설정에 실패했습니다: {e}"
    try:
        user_res = client.auth.get_user()
        uid = user_res.user.id if user_res and user_res.user else None
    except Exception:
        uid = None
    if not uid:
        return False, "세션 정보를 확인할 수 없습니다. 처음부터 다시 시도해주세요."

    admin_client = get_admin_client()
    insert_client = admin_client if admin_client is not None else client
    try:
        insert_client.table("profiles").insert({
            "id": uid,
            "student_no": student_no,
            "school_email": school_email,
            "name": name,
            "identity": "학생",
            "is_admin": False,
        }).execute()
    except Exception as e:
        return False, f"프로필 저장에 실패했습니다: {e}"
    ss.current_user_id = uid
    ss.profile_cache = None
    try:
        session = client.auth.get_session()
    except Exception:
        session = None
    save_auth_cookies(session)
    return True, "인증이 완료되고 계정이 생성되었습니다."


def student_signin(student_no: str, password: str):
    profile = profile_exists_by_student_no(student_no)
    if not profile or not profile.get("school_email"):
        return False, "등록되지 않은 학번입니다. 학교 이메일 인증을 먼저 진행해주세요."
    client = get_user_client()
    try:
        auth_res = client.auth.sign_in_with_password(
            {"email": profile["school_email"], "password": password}
        )
    except Exception:
        return False, "학번 또는 비밀번호가 올바르지 않습니다."
    if auth_res.user is None:
        return False, "학번 또는 비밀번호가 올바르지 않습니다."
    ss.current_user_id = auth_res.user.id
    ss.profile_cache = None
    save_auth_cookies(auth_res.session)
    return True, "로그인되었습니다."


# ---------- 교직원 로그인/가입 ----------
def get_staff_code_info(code: str):
    client = get_user_client()
    try:
        res = client.table("staff_codes").select("*").eq("code", code).execute()
    except Exception as e:
        st.error(_friendly_db_error(e))
        st.stop()
    return res.data[0] if res.data else None


def staff_username_exists(username: str) -> bool:
    client = get_user_client()
    try:
        res = (
            client.table("profiles")
            .select("id")
            .eq("staff_username", username)
            .execute()
        )
    except Exception as e:
        st.error(_friendly_db_error(e))
        st.stop()
    return bool(res.data)


def staff_signup(code: str, name: str, username: str, password: str):
    username = username.strip()
    if staff_username_exists(username):
        return False, "이미 사용 중인 아이디입니다. 다른 아이디를 입력해주세요."

    client = get_user_client()
    try:
        auth_res = client.auth.sign_up(
            {"email": staff_login_email(username), "password": password}
        )
    except Exception as e:
        return False, f"계정 생성에 실패했습니다: {e}"
    user = auth_res.user
    if user is None or auth_res.session is None:
        return False, (
            "계정은 만들어졌지만 로그인 세션이 발급되지 않았습니다. "
            "Supabase Authentication > Providers > Email 에서 "
            "'Confirm email' 옵션이 꺼져 있는지 확인해주세요."
        )

    admin_client = get_admin_client()
    insert_client = admin_client if admin_client is not None else client
    try:
        insert_client.table("profiles").insert({
            "id": user.id,
            "staff_code": code,
            "staff_username": username,
            "name": name,
            "identity": "교직원",
            "is_admin": False,
        }).execute()
        insert_client.table("staff_codes").update({"used_by": user.id}).eq("code", code).execute()
    except Exception as e:
        return False, f"프로필 저장에 실패했습니다: {e}"
    ss.current_user_id = user.id
    ss.profile_cache = None
    save_auth_cookies(auth_res.session)
    return True, "계정이 생성되고 로그인되었습니다."


def staff_signin(username: str, password: str):
    client = get_user_client()
    try:
        auth_res = client.auth.sign_in_with_password(
            {"email": staff_login_email(username), "password": password}
        )
    except Exception:
        return False, "아이디 또는 비밀번호가 올바르지 않습니다."
    if auth_res.user is None:
        return False, "아이디 또는 비밀번호가 올바르지 않습니다."
    ss.current_user_id = auth_res.user.id
    ss.profile_cache = None
    save_auth_cookies(auth_res.session)
    return True, "로그인되었습니다."


def logout():
    try:
        get_user_client().auth.sign_out()
    except Exception:
        pass
    ss.current_user_id = None
    ss.profile_cache = None
    reset_login_steps()
    clear_auth_cookies()
    go("메인")


# ----------------------------------------------------------------------
# 상단바 + 우측 슬라이드 드로어(햄버거 메뉴)
# ----------------------------------------------------------------------
PUBLIC_PAGES = [
    ("메인", "🏠", "home"), ("프로그램", "🎤", "programs"),
    ("시간표", "📅", "schedule"), ("부스 정보", "🏪", "booths"), ("랜덤 추천", "🎲", "random"),
    ("오시는 길", "📍", "directions"), ("공지사항", "📢", "notices"), ("FAQ", "❓", "faq"),
]

# 사이드바(드로어) 메뉴에만 노출되는 페이지들.
DRAWER_ONLY_PAGES = [
    ("디지털 방문증", "🎫", "pass"),
    ("인사말", "💌", "greeting"),
]

SLUG_BY_NAME = {name: slug for (name, icon, slug) in PUBLIC_PAGES + DRAWER_ONLY_PAGES}

NAV_SLUGS = {slug: name for (name, icon, slug) in PUBLIC_PAGES + DRAWER_ONLY_PAGES}
NAV_SLUGS.update({"login": "로그인", "mypage": "마이페이지", "admin": "관리자 페이지",
                   "booth_add": "부스 등록", "notice_add": "공지사항 등록",
                   "program_add": "프로그램 등록", "schedule_add": "시간표 등록",
                   "logout": "__logout__"})


def handle_nav_query_param():
    qp = st.query_params
    slug = qp.get("nav")
    if slug:
        target = NAV_SLUGS.get(slug)
        if target == "__logout__":
            logout()
        elif target:
            go(target)
        st.query_params.clear()


def render_topbar_and_drawer():
    user = current_user()
    admin = is_admin()

    links_html = ""
    for name, icon, slug in PUBLIC_PAGES:
        if name == "메인":
            continue
        target_name = NAV_SLUGS.get(slug, name)
        active = " bk-active" if ss.page == target_name else ""
        links_html += f'<a class="bk-drawer-link{active}" href="?nav={slug}" target="_self">{icon} {name}</a>'

    for name, icon, slug in DRAWER_ONLY_PAGES:
        target_name = NAV_SLUGS.get(slug, name)
        active = " bk-active" if ss.page == target_name else ""
        links_html += f'<a class="bk-drawer-link{active}" href="?nav={slug}" target="_self">{icon} {name}</a>'

    links_html += '<hr class="bk-drawer-divider">'

    if user is None:
        links_html += '<a class="bk-drawer-link" href="?nav=login" target="_self">🔐 로그인 / 인증</a>'
    else:
        badge = "👑 관리자" if admin else user["identity"]
        links_html += f'<div class="bk-drawer-user">{user["name"]}님 · {badge}</div>'
        active_my = " bk-active" if ss.page == "마이페이지" else ""
        links_html += f'<a class="bk-drawer-link{active_my}" href="?nav=mypage" target="_self">👤 마이페이지</a>'
        if admin:
            active_admin = " bk-active" if ss.page == "관리자 페이지" else ""
            links_html += f'<a class="bk-drawer-link{active_admin}" href="?nav=admin" target="_self">👑 관리자 페이지</a>'
        links_html += '<a class="bk-drawer-link" href="?nav=logout" target="_self">🚪 로그아웃</a>'

    html = f"""
    <input type="checkbox" id="bk-drawer-toggle" class="bk-drawer-checkbox">
    <div class="bk-topbar">
        <a class="bk-brand" href="?nav=home" target="_self" style="text-decoration:none;">
            <img src="{LOGO_DATA_URI}" class="bk-brand-logo" alt="경복고등학교 로고">
            <span>경복고등학교 {FESTIVAL_NAME}</span>
        </a>
        <label for="bk-drawer-toggle" class="bk-hamburger">☰</label>
    </div>
    <label for="bk-drawer-toggle" class="bk-backdrop"></label>
    <nav class="bk-drawer">
        <div class="bk-drawer-head">
            <span>메뉴</span>
            <label for="bk-drawer-toggle" class="bk-drawer-close">✕</label>
        </div>
        {links_html}
    </nav>
    """
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# 페이지 : 메인
# ----------------------------------------------------------------------
def page_main():
    hc1, hc2 = st.columns([2.6, 1])
    with hc1:
        st.markdown(
            f"""
            <div class="bk-hero">
                <div class="eyebrow">2025</div>
                <h1>경복고등학교 {FESTIVAL_NAME}</h1>
                <div class="slogan">{FESTIVAL_SLOGAN}</div>
                <div class="meta">📅 {FESTIVAL_DATE.strftime('%Y. %m. %d')}(금)</div>
                <div class="meta">📍 경복고등학교 교내 일대</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hc2:
        render_dday_box()

    st.write("")
    st.markdown('<div class="bk-iconmenu">', unsafe_allow_html=True)
    icon_cols = st.columns(6)
    for col, (name, icon, slug) in zip(icon_cols, PUBLIC_PAGES[1:]):
        with col:
            if st.button(f"{icon}\n\n{name}", key=f"iconmenu-{name}", use_container_width=True):
                go(name)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 메인 페이지 프로그램 박스
    # 프로그램이 없어도 박스 자체는 항상 표시해, 메인 화면에서 프로그램 영역을 바로 확인할 수 있게 합니다.
    main_programs = fetch_programs()
    st.markdown('<div class="bk-section-title">🎤 프로그램</div>', unsafe_allow_html=True)
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)

    if main_programs:
        for p in main_programs[:4]:
            st.markdown(
                f"<div style='padding:10px 0;border-bottom:1px solid #EEF0F5;'>"
                f"<div style='font-weight:800;font-size:15px;'>{p['icon']} {p['name']}</div>"
                f"<div style='color:{MUTED};font-size:13px;margin-top:3px;'>"
                f"{p['date']} · {p['time']} · {p['place']}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f"<div style='padding:16px 0;color:{MUTED};font-size:14px;'>"
            "등록된 프로그램이 없습니다.</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<a class='bk-card-btn' href='?nav={SLUG_BY_NAME['프로그램']}' target='_self'>전체 프로그램 보기 →</a>",
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # 시간표도 DB에 등록된 내용만 표시합니다.
    st.markdown('<div class="bk-section-title">📅 시간표</div>', unsafe_allow_html=True)
    grouped_main = fetch_schedule_by_day()
    if grouped_main:
        first_day = list(grouped_main.keys())[0]
        schedule_items_html = "".join(
            f"<div style='padding:6px 0;border-bottom:1px solid #EEF0F5;font-size:13px;'>"
            f"<b>{it['time']}</b>&nbsp;&nbsp;{it['program']} "
            f"<span style='color:{MUTED};'>({it['place']})</span></div>"
            for it in grouped_main[first_day][:4]
        )
    else:
        schedule_items_html = f"<div style='color:{MUTED};font-size:13px;'>등록된 시간표가 없습니다.</div>"
    st.markdown(
        f"""
        <div class="bk-card">
            {schedule_items_html}
            <a class="bk-card-btn" href="?nav={SLUG_BY_NAME['시간표']}" target="_self">전체 시간표 보기 →</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="bk-section-title">📢 공지사항</div>', unsafe_allow_html=True)
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    main_notices = fetch_notices("member" if current_user() is not None else "public")
    if not main_notices:
        st.write("등록된 공지사항이 없습니다.")
    for n in main_notices[:4]:
        badge = "<span class='bk-badge-new'>NEW</span>" if n.get("new") else ""
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #EEF0F5;'>"
            f"<div>{n['title']}{badge}</div><div style='color:{MUTED};font-size:13px;'>{n['date']}</div></div>",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="bk-section-title">🏪 부스 정보</div>', unsafe_allow_html=True)
    main_booths = fetch_booths()
    if not main_booths:
        st.markdown('<div class="bk-card">등록된 부스가 아직 없습니다.</div>', unsafe_allow_html=True)
    else:
        bcols = st.columns(4)
        for col, b in zip(bcols, main_booths[:4]):
            with col:
                img_html = booth_media_html(b, height="110px")
                st.markdown(
                    f"""
                    <div class="bk-card" style="text-align:center;">
                        {img_html}
                        <div style="font-weight:800;margin-top:4px;">{b['name']}</div>
                        <div style="color:{MUTED};font-size:13px;">{b['category']}</div>
                    </div>
                    """, unsafe_allow_html=True,
                )
    if st.button("더 많은 부스 보기 →", key="btn-booths"):
        go("부스 정보"); st.rerun()

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 디지털 방문증 (사이드바 전용)
#  - 회원: 로그인한 회원의 이름을 자동으로 표시합니다.
#  - 비회원: 이름을 직접 입력하면 이 기기(브라우저)의 쿠키에 저장되어,
#            같은 폰/브라우저로 다시 접속해도 입력했던 이름이 유지됩니다.
# ----------------------------------------------------------------------
def page_visitor_pass():
    st.markdown('<div class="bk-section-title">🎫 디지털 방문증</div>', unsafe_allow_html=True)
    user = current_user()
    is_member = user is not None
    visitor_name = ((user.get("name") or "").strip() if is_member else get_guest_pass_name())
    date_str = FESTIVAL_DATE.strftime("%Y. %m. %d")
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][FESTIVAL_DATE.weekday()]
    day_num = FESTIVAL_DATE.day
    weekday_eng = FESTIVAL_DATE.strftime("%a").upper()
    if visitor_name:
        name_html = f'<div class="bk-pass-name-box">{visitor_name}<span class="bk-pass-name-type">{"회원" if is_member else "비회원"}</span></div>'
    else:
        name_html = '<div class="bk-pass-name-box empty">이름 미등록</div>'

    st.markdown(f"""
    <div class="bk-pass-wrap"><div class="bk-pass-card">
      <div class="bk-pass-top">
        <div class="bk-pass-top-label">KYUNGBOCK HIGH SCHOOL · 1921</div>
        <img src="{LOGO_SVG_DATA_URI}" class="bk-pass-emblem" alt="경복고등학교 로고">
        <div class="bk-pass-title-main">{FESTIVAL_NAME}</div>
        <div class="bk-pass-subtitle">DIGITAL VISITOR PASS · 2026</div>
        <div class="bk-pass-rule"><span></span><b>✦</b><span></span></div>
      </div>
      <div class="bk-pass-perforation"></div>
      <div class="bk-pass-bottom">
        <div class="bk-pass-bottom-left">
          <div class="bk-pass-bl-title">VISITOR INFORMATION</div>
          <div class="bk-pass-meta-row"><b>📍 장소</b>&nbsp; 경복고등학교 교내</div>
          <div class="bk-pass-name-label">방문자 이름</div>
          {name_html}
          <div class="bk-pass-meta-row date-row"><b>📅 일시</b>&nbsp; {date_str} ({weekday_kr})</div>
        </div>
        <div class="bk-pass-vdivider"></div>
        <div class="bk-pass-bottom-right">
          <div class="bk-pass-date-label">OCT</div>
          <div class="bk-pass-date-num">{day_num:02d}</div>
          <div class="bk-pass-weekday-eng">{weekday_eng}</div>
        </div>
      </div>
      <div class="bk-pass-footer"><span>BUKAKJE 2026</span><span>ADMIT ONE</span></div>
    </div></div>
    """, unsafe_allow_html=True)

    if is_member:
        st.caption("회원 이름은 로그인한 계정 이름으로 자동 표시됩니다.")
    else:
        st.markdown('<div class="bk-pass-register">', unsafe_allow_html=True)
        st.markdown("### ✏️ 방문자 이름 등록")
        st.caption("저장하면 같은 휴대폰의 같은 브라우저에서 다시 접속해도 이름이 자동으로 표시됩니다.")
        with st.form("guest_pass_name_form", clear_on_submit=False):
            guest_input = st.text_input("방문자 이름", value=visitor_name, placeholder="이름을 입력하세요", max_chars=20, key="guest_pass_name_input")
            submitted = st.form_submit_button("방문증에 이름 등록하기", use_container_width=True)
        if submitted:
            clean_name = guest_input.strip()
            if not clean_name:
                st.error("이름을 입력해주세요.")
            else:
                save_guest_pass_name(clean_name)
                st.rerun()
        if visitor_name and st.button("저장된 이름 삭제", use_container_width=True, key="delete_guest_pass_name"):
            save_guest_pass_name("")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# 페이지 : 인사말 (사이드바 전용)
# ----------------------------------------------------------------------
def page_greeting():
    st.markdown('<div class="bk-section-title">💌 인사말</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🎓 학생회장단 인사말", "🏫 교장선생님 인사말"])

    with tab1:
        st.markdown(f"""
안녕하세요, 경복고등학교 학생을 대표하는 학생회장단입니다.

먼저 저희 **{FESTIVAL_NAME}**을 찾아주신 모든 분들께 진심으로 감사드립니다.
이번 축제는 학생들이 오랜 시간 함께 고민하고 준비한 만큼, 공연·체험·전시 등
다양한 프로그램을 통해 즐거운 추억을 만드실 수 있도록 최선을 다해 준비했습니다.

학생들의 열정과 노력이 담긴 하루하루가 여러분께 즐거운 시간이 되기를 바라며,
안전하고 즐거운 축제가 될 수 있도록 끝까지 함께해 주시면 감사하겠습니다.

**"{FESTIVAL_SLOGAN}"** — 이 슬로건처럼, 우리 모두가 하나 되는 축제를 만들어가겠습니다.

감사합니다.

**경복고등학교 학생회장단 일동**
        """)

    with tab2:
        st.markdown(f"""
안녕하십니까, 경복고등학교장입니다.

한 해 동안 학업에 정진해 온 우리 학생들이 그동안 갈고닦은 끼와 재능을
마음껏 펼치는 뜻깊은 자리, **{FESTIVAL_NAME}**에 오신 것을 진심으로 환영합니다.

이 축제는 학생들이 스스로 기획하고 준비하는 과정에서 협동과 배려, 그리고
책임감을 배우는 소중한 교육의 장이기도 합니다. 학생, 학부모님, 그리고
지역사회 여러분의 관심과 성원이 있었기에 오늘의 축제가 있을 수 있었습니다.

앞으로도 학생들이 마음껏 꿈을 펼칠 수 있는 학교가 될 수 있도록
교직원 모두 최선을 다하겠습니다. 축제 기간 동안 안전에 유의하시고,
즐겁고 뜻깊은 시간 보내시기를 바랍니다.

감사합니다.

**경복고등학교장**
        """)

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 프로그램
# ----------------------------------------------------------------------
def page_programs():
    st.markdown('<div class="bk-section-title">🎤 프로그램</div>', unsafe_allow_html=True)

    admin = is_admin()
    all_programs = fetch_programs()

    categories = ["전체", "공연", "체험", "전시", "기타"]
    cat = st.radio("카테고리", categories, horizontal=True, label_visibility="collapsed")
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)

    filtered = all_programs if cat == "전체" else [p for p in all_programs if p["category"] == cat]
    if not filtered:
        st.info("해당 카테고리의 프로그램이 없습니다.")
    for p in filtered:
        with st.expander(f"{p['icon']}  {p['name']}  ·  {p['date']} {p['time']}  ·  {p['place']}"):
            st.markdown(f"<span class='bk-chip'>{p['category']}</span>", unsafe_allow_html=True)
            st.write(p["desc"])

            # ----------------------------------------------------------
            # 관리자에게만 보이는 수정/삭제 컨트롤 (부스/공지사항과 동일한 방식)
            # ----------------------------------------------------------
            if admin:
                st.markdown("---")
                cat_options = ["공연", "체험", "전시", "기타"]
                default_idx = cat_options.index(p["category"]) if p["category"] in cat_options else 3
                with st.form(f"program_edit_form_{p['id']}"):
                    new_name = st.text_input("프로그램 이름", value=p["name"], key=f"pg_name_{p['id']}")
                    new_cat = st.selectbox("카테고리", cat_options, index=default_idx, key=f"pg_cat_{p['id']}")
                    new_date = st.text_input("날짜", value=p["date"], key=f"pg_date_{p['id']}")
                    new_time = st.text_input("시간", value=p["time"], key=f"pg_time_{p['id']}")
                    new_place = st.text_input("장소", value=p["place"], key=f"pg_place_{p['id']}")
                    new_desc = st.text_area("설명", value=p["desc"], key=f"pg_desc_{p['id']}")
                    new_icon = st.text_input(
                        "아이콘(이모티콘)", value=p["icon"], max_chars=8, key=f"pg_icon_{p['id']}"
                    )
                    pec1, pec2 = st.columns(2)
                    save_clicked = pec1.form_submit_button("💾 저장", use_container_width=True)
                    delete_clicked = pec2.form_submit_button("🗑️ 삭제", use_container_width=True)

                if save_clicked:
                    ok, msg = update_program(p["id"], {
                        "name": new_name.strip() or p["name"], "category": new_cat,
                        "date": new_date, "time": new_time, "place": new_place,
                        "desc": new_desc, "icon": new_icon.strip() or "🎫",
                    })
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

                if delete_clicked:
                    ok, msg = delete_program(p["id"])
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 관리자에게만 보이는 우측 하단 + 버튼 → 프로그램 등록 페이지로 이동
    if admin:
        st.markdown(
            '<a class="bk-fab" href="?nav=program_add" target="_self" title="프로그램 추가">+</a>',
            unsafe_allow_html=True,
        )

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 프로그램 등록 (관리자 전용, 프로그램 페이지의 + 버튼에서 진입)
# ----------------------------------------------------------------------
def page_program_add():
    if not is_admin():
        st.error("관리자만 접근할 수 있는 페이지입니다.")
        if st.button("프로그램으로 돌아가기"):
            go("프로그램"); st.rerun()
        render_footer()
        return

    st.markdown('<div class="bk-section-title">➕ 프로그램 등록</div>', unsafe_allow_html=True)
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    with st.form("program_add_page_form"):
        pn = st.text_input("프로그램 이름")
        pcat = st.selectbox("카테고리", ["공연", "체험", "전시", "기타"])
        pdate = st.text_input("날짜", placeholder="예: 9.5(금)")
        ptime = st.text_input("시간", placeholder="예: 14:00")
        pplace = st.text_input("장소")
        pdesc = st.text_area("설명")
        picon = st.text_input("아이콘(이모티콘)", value="🎫", max_chars=8)
        c1, c2 = st.columns(2)
        submit = c1.form_submit_button("등록", use_container_width=True)
        cancel = c2.form_submit_button("취소", use_container_width=True)

    if cancel:
        go("프로그램"); st.rerun()

    if submit:
        if not pn.strip():
            st.error("프로그램 이름을 입력해주세요.")
        else:
            ok, msg = add_program({"name": pn.strip(), "category": pcat, "date": pdate,
                                    "time": ptime, "place": pplace, "desc": pdesc,
                                    "icon": picon.strip() or "🎫"})
            if ok:
                st.success(msg)
                go("프로그램"); st.rerun()
            else:
                st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 시간표
# ----------------------------------------------------------------------
def page_schedule():
    st.markdown('<div class="bk-section-title">📅 시간표</div>', unsafe_allow_html=True)
    st.caption("로그인 없이 누구나 확인할 수 있습니다.")

    admin = is_admin()
    grouped = fetch_schedule_by_day()

    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    if not grouped:
        st.info("등록된 시간표가 없습니다.")
    else:
        days = list(grouped.keys())
        tabs = st.tabs(days)
        for tab, day in zip(tabs, days):
            with tab:
                for it in grouped[day]:
                    st.markdown(
                        f"<div style='padding:8px 0;border-bottom:1px solid #EEF0F5;'>"
                        f"<span class='bk-pill'>{it['time']}</span>&nbsp;&nbsp;"
                        f"<b>{it['program']}</b> <span style='color:{MUTED};'>({it['place']})</span></div>",
                        unsafe_allow_html=True,
                    )
                    if admin:
                        with st.expander(f"✏️ 수정 / 삭제 — {it['time']} {it['program']}"):
                            with st.form(f"schedule_edit_form_{it['id']}"):
                                new_day = st.text_input("날짜", value=it["day"], key=f"sc_day_{it['id']}")
                                new_time = st.text_input("시간", value=it["time"], key=f"sc_time_{it['id']}")
                                new_program = st.text_input("프로그램", value=it["program"], key=f"sc_program_{it['id']}")
                                new_place = st.text_input("장소", value=it["place"], key=f"sc_place_{it['id']}")
                                sec1, sec2 = st.columns(2)
                                save_clicked = sec1.form_submit_button("💾 저장", use_container_width=True)
                                delete_clicked = sec2.form_submit_button("🗑️ 삭제", use_container_width=True)

                            if save_clicked:
                                ok, msg = update_schedule_item(it["id"], {
                                    "day": new_day, "time": new_time,
                                    "program": new_program, "place": new_place,
                                })
                                (st.success if ok else st.error)(msg)
                                if ok:
                                    st.rerun()

                            if delete_clicked:
                                ok, msg = delete_schedule_item(it["id"])
                                (st.success if ok else st.error)(msg)
                                if ok:
                                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    lines = []
    for day, items in grouped.items():
        lines.append(f"[{day}]")
        for it in items:
            lines.append(f"{it['time']}  {it['program']}  ({it['place']})")
        lines.append("")
    if lines:
        st.download_button("⬇️ 전체 시간표 다운로드", data="\n".join(lines),
                            file_name="북악제_시간표.txt", mime="text/plain")

    # 관리자에게만 보이는 우측 하단 + 버튼 → 시간표 등록 페이지로 이동
    if admin:
        st.markdown(
            '<a class="bk-fab" href="?nav=schedule_add" target="_self" title="시간표 추가">+</a>',
            unsafe_allow_html=True,
        )

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 시간표 등록 (관리자 전용, 시간표 페이지의 + 버튼에서 진입)
# ----------------------------------------------------------------------
def page_schedule_add():
    if not is_admin():
        st.error("관리자만 접근할 수 있는 페이지입니다.")
        if st.button("시간표로 돌아가기"):
            go("시간표"); st.rerun()
        render_footer()
        return

    st.markdown('<div class="bk-section-title">➕ 시간표 등록</div>', unsafe_allow_html=True)
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    with st.form("schedule_add_page_form"):
        sday = st.text_input("날짜", placeholder="예: 9.5(금)")
        stime = st.text_input("시간", placeholder="예: 10:00")
        sprogram = st.text_input("프로그램")
        splace = st.text_input("장소")
        c1, c2 = st.columns(2)
        submit = c1.form_submit_button("등록", use_container_width=True)
        cancel = c2.form_submit_button("취소", use_container_width=True)

    if cancel:
        go("시간표"); st.rerun()

    if submit:
        if not sday.strip() or not stime.strip() or not sprogram.strip():
            st.error("날짜, 시간, 프로그램은 필수입니다.")
        else:
            ok, msg = add_schedule_item({"day": sday.strip(), "time": stime.strip(),
                                          "program": sprogram.strip(), "place": splace})
            if ok:
                st.success(msg)
                go("시간표"); st.rerun()
            else:
                st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 부스 정보
# ----------------------------------------------------------------------
def page_booths():
    st.markdown('<div class="bk-section-title">🏪 부스 정보</div>', unsafe_allow_html=True)
    st.caption("부스 신청 기능은 제공하지 않으며, 운영 부스 정보만 안내합니다. (갤러리 기능 없음)")

    admin = is_admin()
    all_booths = fetch_booths()

    fcol1, fcol2 = st.columns([1, 2])
    with fcol1:
        categories = ["전체"] + sorted({b["category"] for b in all_booths if b.get("category")})
        selected_cat = st.selectbox("카테고리", categories, label_visibility="collapsed")
    with fcol2:
        keyword = st.text_input("부스 이름 검색", placeholder="🔍 부스 이름으로 검색", label_visibility="collapsed")

    booths = all_booths
    if selected_cat != "전체":
        booths = [b for b in booths if b.get("category") == selected_cat]
    if keyword.strip():
        kw = keyword.strip().lower()
        booths = [b for b in booths if kw in b["name"].lower()]

    if not all_booths:
        st.info("아직 등록된 부스가 없습니다.")
    elif not booths:
        st.info("조건에 맞는 부스가 없습니다.")
    else:
        cols = st.columns(2)
        for i, b in enumerate(booths):
            with cols[i % 2]:
                img_html = booth_media_html(b, height="260px")
                st.markdown(
                    f"""
                    <div class="bk-card" style="margin-bottom:8px;">
                        {img_html}
                        <div style="font-weight:800;font-size:17px;margin-top:4px;">{b['name']} <span class="bk-chip">{b['category']}</span></div>
                        <div style="color:{MUTED};margin-top:6px;">📍 {b['place']} &nbsp;|&nbsp; 🕒 {b['hours']}</div>
                        <div style="margin-top:8px;">{b['desc']}</div>
                    </div>
                    """, unsafe_allow_html=True,
                )

                if admin:
                    with st.expander("✏️ 이 부스 수정 / 삭제", expanded=False):
                        with st.form(f"booth_page_edit_form_{b['id']}"):
                            new_name = st.text_input("부스 이름", value=b["name"], key=f"bp_name_{b['id']}")
                            new_cat = st.selectbox("카테고리", ["동아리 부스", "먹거리 부스"], index=0 if b.get("category") != "먹거리 부스" else 1, key=f"bp_cat_{b['id']}")
                            new_place = st.text_input("위치", value=b["place"], key=f"bp_place_{b['id']}")
                            new_hours = st.text_input("운영시간", value=b["hours"], key=f"bp_hours_{b['id']}")
                            new_desc = st.text_area("설명", value=b["desc"], key=f"bp_desc_{b['id']}")
                            new_icon = st.text_input(
                                "아이콘(이모티콘)", value=b.get("icon") or "🏪",
                                max_chars=8, key=f"bp_icon_{b['id']}",
                                help="사진을 등록해도 이 아이콘이 사진 위 배지로 함께 표시됩니다. 예: 🍔 🎮 🎨 🎵",
                            )
                            new_image = st.file_uploader(
                                "부스 사진 교체 (선택, 비워두면 기존 사진 유지)",
                                type=["png", "jpg", "jpeg", "gif", "webp"],
                                key=f"bp_image_{b['id']}",
                            )
                            remove_image = st.checkbox(
                                "기존 사진 삭제하고 이모티콘으로 표시",
                                value=False, key=f"bp_remove_image_{b['id']}",
                            ) if b.get("image") else False
                            bec1, bec2 = st.columns(2)
                            save_clicked = bec1.form_submit_button("💾 저장", use_container_width=True)
                            delete_clicked = bec2.form_submit_button("🗑️ 삭제", use_container_width=True)

                        if save_clicked:
                            update_data = {
                                "name": new_name.strip() or b["name"],
                                "category": new_cat,
                                "place": new_place,
                                "hours": new_hours,
                                "desc": new_desc,
                                "icon": new_icon.strip() or "🏪",
                            }
                            if remove_image:
                                update_data["image"] = None
                            elif new_image is not None:
                                b64 = base64.b64encode(new_image.getvalue()).decode("utf-8")
                                update_data["image"] = f"data:{new_image.type};base64,{b64}"
                            ok, msg = update_booth(b["id"], update_data)
                            (st.success if ok else st.error)(msg)
                            if ok:
                                st.rerun()

                        if delete_clicked:
                            ok, msg = delete_booth(b["id"])
                            (st.success if ok else st.error)(msg)
                            if ok:
                                st.rerun()

    if admin:
        st.markdown(
            '<a class="bk-fab" href="?nav=booth_add" target="_self" title="부스 추가">+</a>',
            unsafe_allow_html=True,
        )

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 부스 등록 (관리자 전용, 부스 정보 페이지의 + 버튼에서 진입)
# ----------------------------------------------------------------------
def page_booth_add():
    if not is_admin():
        st.error("관리자만 접근할 수 있는 페이지입니다.")
        if st.button("부스 정보로 돌아가기"):
            go("부스 정보"); st.rerun()
        render_footer()
        return

    st.markdown('<div class="bk-section-title">➕ 부스 등록</div>', unsafe_allow_html=True)
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    with st.form("booth_add_page_form"):
        bn = st.text_input("부스 이름")
        bc = st.selectbox("카테고리", ["동아리 부스", "먹거리 부스"])
        bp = st.text_input("위치")
        bh = st.text_input("운영시간")
        bd = st.text_area("설명")
        b_icon = st.text_input(
            "아이콘(이모티콘)", value="🏪", max_chars=8,
            help="사진을 등록해도 이 아이콘이 사진 위 배지로 함께 표시됩니다. 예: 🍔 🎮 🎨 🎵 ☕",
        )
        b_image = st.file_uploader(
            "부스 사진 (선택, 등록하면 사진과 아이콘이 함께 표시됩니다)",
            type=["png", "jpg", "jpeg", "gif", "webp"], key="booth_add_page_image"
        )
        c1, c2 = st.columns(2)
        submit = c1.form_submit_button("등록", use_container_width=True)
        cancel = c2.form_submit_button("취소", use_container_width=True)

    if cancel:
        go("부스 정보"); st.rerun()

    if submit:
        if not bn.strip():
            st.error("부스 이름을 입력해주세요.")
        else:
            image_data_uri = None
            if b_image is not None:
                b64 = base64.b64encode(b_image.getvalue()).decode("utf-8")
                image_data_uri = f"data:{b_image.type};base64,{b64}"
            ok, msg = add_booth({"name": bn.strip(), "category": bc, "place": bp,
                                  "hours": bh, "desc": bd, "icon": b_icon.strip() or "🏪",
                                  "image": image_data_uri})
            if ok:
                st.success(msg)
                go("부스 정보"); st.rerun()
            else:
                st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 오시는 길
# ----------------------------------------------------------------------
def page_directions():
    st.markdown('<div class="bk-section-title">📍 오시는 길</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.4, 1])

    with c1:
        # 중요한 위치만 표시하고, 지도 중심은 항상 경복고등학교로 잡습니다.
        # 표시 항목: 경복고등학교 / 학교 앞 100m / 통인시장 / 경복궁역
        school_lat = 37.5876963
        school_lon = 126.9717003
        station_lat = 37.575804
        station_lon = 126.973576

        # 통인시장(서울 종로구 자하문로15길 18) 위치
        market_lat = 37.58035
        market_lon = 126.96955

        fmap = folium.Map(
            location=[school_lat, school_lon],
            zoom_start=14,
            min_zoom=14,
            max_zoom=17,
            control_scale=False,
            zoom_control=True,
            tiles="OpenStreetMap",
            width="100%",
            height=360,
        )

        # ① 경복고등학교 — 지도 중심
        folium.Marker(
            [school_lat, school_lon],
            tooltip="경복고등학교",
            popup=folium.Popup(
                "<b>경복고등학교</b><br>서울특별시 종로구 자하문로 17길 33",
                max_width=280,
            ),
            icon=folium.Icon(color="blue", icon="graduation-cap", prefix="fa"),
        ).add_to(fmap)

        # ② 학교 앞 100m — 학교 주변 행사 구역을 한눈에 확인
        folium.Circle(
            [school_lat, school_lon],
            radius=100,
            color="#E67E22",
            weight=2,
            fill=True,
            fill_opacity=0.08,
            tooltip="학교 앞 100m",
        ).add_to(fmap)

        folium.Marker(
            [school_lat + 0.00055, school_lon],
            tooltip="학교 앞 100m",
            popup=folium.Popup("<b>학교 앞 100m</b><br>경복고등학교 기준 반경 100m", max_width=240),
            icon=folium.Icon(color="orange", icon="info-sign"),
        ).add_to(fmap)

        # ③ 통인시장
        folium.Marker(
            [market_lat, market_lon],
            tooltip="통인시장",
            popup=folium.Popup(
                "<b>통인시장</b><br>서울 종로구 자하문로15길 18",
                max_width=240,
            ),
            icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa"),
        ).add_to(fmap)

        # ④ 경복궁역
        folium.Marker(
            [station_lat, station_lon],
            tooltip="경복궁역",
            popup=folium.Popup(
                "<b>경복궁역</b><br>3호선 · 3번 출구",
                max_width=220,
            ),
            icon=folium.Icon(color="red", icon="subway", prefix="fa"),
        ).add_to(fmap)

        # 전체 범위도 경복고등학교가 시각적으로 중심이 되도록 고정합니다.
        fmap.fit_bounds(
            [
                [school_lat - 0.008, school_lon - 0.006],
                [school_lat + 0.008, school_lon + 0.006],
            ],
            padding=(10, 10),
            max_zoom=14,
        )

        map_html = fmap.get_root().render()
        map_html = map_html.replace(
            "<body>",
            '<body style="margin:0;padding:0;background:transparent;overflow:hidden;">'
        )
        components.html(map_html, height=380, scrolling=False)

    with c2:
        st.markdown('<div class="bk-card">', unsafe_allow_html=True)
        st.write(f"**주소**\n\n{ss.site_info['address']}")
        st.markdown("---")
        st.write(f"🚇 **지하철**\n\n{ss.site_info['subway']}")
        st.write(f"🚌 **버스**\n\n{ss.site_info['bus']}")
        st.write(f"🚶 **도보**\n\n{ss.site_info['walk']}")
        st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 공지사항
# ----------------------------------------------------------------------
def page_notices():
    st.markdown('<div class="bk-section-title">📢 공지사항</div>', unsafe_allow_html=True)

    admin = is_admin()
    user = current_user()
    notices = fetch_notices("member" if user is not None else "public")

    if user is None:
        st.caption("🔓 전체 공개 공지만 표시됩니다. 학생·교직원 전용 공지는 로그인 후 확인할 수 있습니다.")
    else:
        st.caption(f"🔐 {user['identity']} 로그인 상태 — 전체 공개 및 학생/교직원 전용 공지를 모두 확인할 수 있습니다.")

    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    if not notices:
        st.info("등록된 공지사항이 없습니다.")
    else:
        for n in notices:
            badge = "<span class='bk-badge-new'>NEW</span>" if n.get("new") else ""
            scope = "전체 공개" if n.get("visibility") == "all" else "학생/교직원 전용"
            with st.expander(f"{n['title']}   ({n['date']})"):
                st.markdown(f"{badge} <span class='bk-chip'>{scope}</span>", unsafe_allow_html=True)
                st.write(n["content"])

                if admin:
                    st.markdown("---")
                    with st.form(f"notice_page_edit_form_{n['id']}"):
                        new_title = st.text_input("제목", value=n["title"], key=f"np_title_{n['id']}")
                        new_content = st.text_area("내용", value=n["content"], key=f"np_content_{n['id']}")
                        new_is_new = st.checkbox("NEW 표시", value=bool(n.get("new")), key=f"np_new_{n['id']}")
                        new_visibility_label = st.radio(
                            "공개 범위", ["전체 공개", "학생/교직원 전용"],
                            index=0 if n.get("visibility") == "all" else 1,
                            horizontal=True, key=f"np_vis_{n['id']}"
                        )
                        new_visibility = "all" if new_visibility_label == "전체 공개" else "members"
                        nec1, nec2 = st.columns(2)
                        save_clicked = nec1.form_submit_button("💾 저장", use_container_width=True)
                        delete_clicked = nec2.form_submit_button("🗑️ 삭제", use_container_width=True)

                    if save_clicked:
                        ok, msg = update_notice(n["id"], new_title.strip() or n["title"], new_content, new_is_new, new_visibility)
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()

                    if delete_clicked:
                        ok, msg = delete_notice(n["id"])
                        (st.success if ok else st.error)(msg)
                        if ok:
                            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if admin:
        st.markdown(
            '<a class="bk-fab" href="?nav=notice_add" target="_self" title="공지사항 추가">+</a>',
            unsafe_allow_html=True,
        )

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 공지사항 등록 (관리자 전용, 공지사항 페이지의 + 버튼에서 진입)
# ----------------------------------------------------------------------
def page_notice_add():
    if not is_admin():
        st.error("관리자만 접근할 수 있는 페이지입니다.")
        if st.button("공지사항으로 돌아가기"):
            go("공지사항"); st.rerun()
        render_footer()
        return

    st.markdown('<div class="bk-section-title">➕ 공지사항 등록</div>', unsafe_allow_html=True)
    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    with st.form("notice_add_page_form"):
        t = st.text_input("제목")
        c = st.text_area("내용")
        is_new = st.checkbox("NEW 표시", value=True)
        visibility_label = st.radio("공개 범위", ["전체 공개", "학생/교직원 전용"], horizontal=True)
        visibility = "all" if visibility_label == "전체 공개" else "members"
        c1, c2 = st.columns(2)
        submit = c1.form_submit_button("등록", use_container_width=True)
        cancel = c2.form_submit_button("취소", use_container_width=True)

    if cancel:
        go("공지사항"); st.rerun()

    if submit:
        if not t.strip():
            st.error("제목을 입력해주세요.")
        else:
            ok, msg = add_notice(t.strip(), c, is_new, visibility)
            if ok:
                st.success(msg)
                go("공지사항"); st.rerun()
            else:
                st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : FAQ
# ----------------------------------------------------------------------
def page_faq():
    st.markdown('<div class="bk-section-title">❓ FAQ</div>', unsafe_allow_html=True)
    st.caption("축제 이용 중 자주 묻는 질문을 확인할 수 있습니다.")
    faqs = fetch_faqs()
    admin = is_admin()

    if not faqs:
        st.info("등록된 FAQ가 없습니다.")
    else:
        for faq in faqs:
            with st.expander(f"❓ {faq['question']}"):
                st.write(faq["answer"])
                if admin:
                    with st.form(f"faq_edit_{faq['id']}"):
                        q = st.text_input("질문", value=faq["question"], key=f"faq_q_{faq['id']}")
                        a = st.text_area("답변", value=faq["answer"], key=f"faq_a_{faq['id']}")
                        c1, c2 = st.columns(2)
                        save = c1.form_submit_button("💾 저장", use_container_width=True)
                        delete = c2.form_submit_button("🗑️ 삭제", use_container_width=True)
                    if save:
                        if not q.strip() or not a.strip():
                            st.error("질문과 답변을 모두 입력해주세요.")
                        else:
                            ok, msg = update_faq(faq["id"], q.strip(), a.strip())
                            (st.success if ok else st.error)(msg)
                            if ok: st.rerun()
                    if delete:
                        ok, msg = delete_faq(faq["id"])
                        (st.success if ok else st.error)(msg)
                        if ok: st.rerun()

    if admin:
        with st.expander("➕ FAQ 추가", expanded=False):
            with st.form("faq_add_form"):
                q = st.text_input("질문")
                a = st.text_area("답변")
                submit = st.form_submit_button("등록", use_container_width=True)
            if submit:
                if not q.strip() or not a.strip():
                    st.error("질문과 답변을 모두 입력해주세요.")
                else:
                    ok, msg = add_faq(q.strip(), a.strip())
                    (st.success if ok else st.error)(msg)
                    if ok: st.rerun()

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 랜덤 부스 추천
# ----------------------------------------------------------------------
def page_random():
    st.markdown('<div class="bk-section-title">🎲 랜덤 부스 추천</div>', unsafe_allow_html=True)
    booths = fetch_booths()
    if not booths:
        st.info("아직 등록된 부스가 없습니다.")
        render_footer()
        return

    if "random_booth" not in ss:
        ss.random_booth = None

    st.markdown('<div class="bk-card" style="text-align:center;">', unsafe_allow_html=True)
    st.markdown("### 🎲 어디로 갈까요?")
    st.write("버튼을 누르면 운영 중인 부스 중 하나를 랜덤으로 추천합니다.")
    if st.button("🎲 랜덤으로 뽑기", use_container_width=True):
        ss.random_booth = random.choice(booths)

    if ss.random_booth:
        b = ss.random_booth
        img_html = booth_media_html(b, height="220px")
        st.markdown(
            f"""<div style='margin-top:18px;'>{img_html}
            <h2>{b['icon']} {b['name']}</h2>
            <div class='bk-chip'>{b['category']}</div>
            <p>📍 {b['place']} &nbsp;|&nbsp; 🕒 {b['hours']}</p>
            <p>{b['desc']}</p></div>""", unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 로그인 / 인증  (학생: 학번+비밀번호 / 교직원: 아이디+비밀번호, Supabase Auth)
# ----------------------------------------------------------------------
def page_login():
    st.markdown('<div class="bk-section-title">🔐 로그인 / 인증</div>', unsafe_allow_html=True)

    user = current_user()
    if user is not None:
        st.info(f"이미 **{user['name']}**님으로 로그인되어 있습니다.")
        if st.button("마이페이지로 이동"):
            go("마이페이지"); st.rerun()
        render_footer()
        return

    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["👤 학생 인증", "🧑‍🏫 교직원 인증"])

    with tab1:
        if ss.student_step == "check":
            st.caption("학번과 이름을 입력해주세요. 처음이라면 학교이메일 인증을 진행하게 됩니다.")
            with st.form("student_check_form"):
                s_no = st.text_input("학번(학교아이디)", placeholder="예: 20301")
                s_name = st.text_input("이름")
                submitted = st.form_submit_button("다음", use_container_width=True)
            if submitted:
                if not s_no or not s_name:
                    st.error("학번과 이름을 모두 입력해주세요.")
                else:
                    existing = profile_exists_by_student_no(s_no.strip())
                    ss.pending_student_no = s_no.strip()
                    ss.pending_student_name = s_name.strip()
                    ss.student_step = "password_existing" if existing else "email_input"
                    st.rerun()

        elif ss.student_step == "email_input":
            st.success(f"학번 **{ss.pending_student_no}**({ss.pending_student_name})은(는) 처음 로그인합니다. 학교 이메일을 입력해주세요.")
            with st.form("student_email_form"):
                s_email = st.text_input("학교 이메일", placeholder="예: 20301@kbhs.hs.kr")
                c1, c2 = st.columns(2)
                submit = c1.form_submit_button("인증코드 받기", use_container_width=True)
                back = c2.form_submit_button("← 뒤로", use_container_width=True)
            if back:
                reset_login_steps(); st.rerun()
            if submit:
                if not s_email or "@" not in s_email:
                    st.error("학교 이메일을 올바르게 입력해주세요.")
                else:
                    ok, msg = send_student_otp(s_email.strip())
                    if ok:
                        ss.pending_student_email = s_email.strip()
                        ss.student_step = "otp_verify"
                        st.rerun()
                    else:
                        st.error(msg)

        elif ss.student_step == "otp_verify":
            st.write(f"**{ss.pending_student_email}** 로 전송된 인증코드를 입력해주세요.")
            with st.form("student_otp_form"):
                code = st.text_input("인증코드 (6자리)")
                c1, c2, c3 = st.columns(3)
                submit = c1.form_submit_button("확인", use_container_width=True)
                resend = c2.form_submit_button("재전송", use_container_width=True)
                back = c3.form_submit_button("← 뒤로", use_container_width=True)
            if back:
                reset_login_steps(); st.rerun()
            if resend:
                ok, msg = send_student_otp(ss.pending_student_email)
                (st.success if ok else st.error)(msg)
            if submit:
                if not code:
                    st.error("인증코드를 입력해주세요.")
                else:
                    ok, msg = verify_student_otp(ss.pending_student_email, code)
                    if ok:
                        ss.student_step = "password_new"
                        st.rerun()
                    else:
                        st.error(msg)

        elif ss.student_step == "password_new":
            st.success("이메일 인증이 완료되었습니다. 앞으로 로그인에 사용할 비밀번호를 만들어주세요.")
            with st.form("student_signup_form"):
                pw1 = st.text_input("비밀번호 (6자 이상)", type="password")
                pw2 = st.text_input("비밀번호 확인", type="password")
                submit = st.form_submit_button("계정 생성 및 로그인", use_container_width=True)
            if submit:
                if len(pw1) < 6:
                    st.error("비밀번호는 6자 이상이어야 합니다.")
                elif pw1 != pw2:
                    st.error("비밀번호가 서로 일치하지 않습니다.")
                else:
                    ok, msg = finish_student_signup(
                        ss.pending_student_no, ss.pending_student_name,
                        ss.pending_student_email, pw1,
                    )
                    if ok:
                        reset_login_steps()
                        st.success(msg)
                        go("마이페이지"); st.rerun()
                    else:
                        st.error(msg)

        elif ss.student_step == "password_existing":
            st.write(f"**{ss.pending_student_name}**님, 비밀번호를 입력해주세요.")
            with st.form("student_signin_form"):
                pw = st.text_input("비밀번호", type="password")
                c1, c2 = st.columns(2)
                submit = c1.form_submit_button("로그인", use_container_width=True)
                back = c2.form_submit_button("← 뒤로", use_container_width=True)
            if back:
                reset_login_steps(); st.rerun()
            if submit:
                ok, msg = student_signin(ss.pending_student_no, pw)
                if ok:
                    reset_login_steps()
                    go("마이페이지"); st.rerun()
                else:
                    st.error(msg)

    with tab2:
        staff_sub1, staff_sub2 = st.tabs(["🆕 최초 등록 (인증코드)", "🔑 로그인 (아이디)"])

        with staff_sub1:
            if ss.staff_step == "check":
                st.caption("미리 발급받은 교직원 인증코드를 입력해주세요. (최초 1회만 필요합니다)")
                with st.form("staff_check_form"):
                    code = st.text_input("인증코드", placeholder="예: BK26-A7Q9")
                    submitted = st.form_submit_button("다음", use_container_width=True)
                if submitted:
                    code = code.strip()
                    info = get_staff_code_info(code)
                    if not info:
                        st.error("존재하지 않는 인증코드입니다.")
                    elif not info["active"]:
                        st.error("비활성화된 인증코드입니다.")
                    elif info.get("used_by"):
                        st.error("이미 등록에 사용된 인증코드입니다. '로그인 (아이디)' 탭에서 아이디+비밀번호로 로그인해주세요.")
                    else:
                        preset_name = (info.get("name") or "").strip()
                        if not preset_name:
                            st.error("이 인증코드에는 담당 선생님 이름이 등록되어 있지 않습니다. 관리자에게 문의해주세요.")
                        else:
                            ss.pending_staff_code = code
                            ss.pending_staff_name = preset_name
                            ss.staff_step = "account_new"
                            st.rerun()

            elif ss.staff_step == "account_new":
                st.success(f"인증코드 확인 완료 — **{ss.pending_staff_name}**님, 앞으로 로그인에 사용할 아이디와 비밀번호를 만들어주세요.")
                with st.form("staff_signup_form"):
                    s_username = st.text_input("아이디(로그인 ID)", placeholder="예: kimteacher")
                    pw1 = st.text_input("비밀번호 (6자 이상)", type="password")
                    pw2 = st.text_input("비밀번호 확인", type="password")
                    c1, c2 = st.columns(2)
                    submit = c1.form_submit_button("계정 생성 및 로그인", use_container_width=True)
                    back = c2.form_submit_button("← 뒤로", use_container_width=True)
                if back:
                    reset_login_steps(); st.rerun()
                if submit:
                    if not s_username.strip():
                        st.error("아이디를 입력해주세요.")
                    elif len(pw1) < 6:
                        st.error("비밀번호는 6자 이상이어야 합니다.")
                    elif pw1 != pw2:
                        st.error("비밀번호가 서로 일치하지 않습니다.")
                    else:
                        ok, msg = staff_signup(
                            ss.pending_staff_code, ss.pending_staff_name, s_username, pw1,
                        )
                        if ok:
                            reset_login_steps()
                            st.success(msg)
                            go("마이페이지"); st.rerun()
                        else:
                            st.error(msg)

        with staff_sub2:
            st.caption("이미 인증코드로 등록을 마치셨다면, 그때 만든 아이디+비밀번호로 로그인해주세요.")
            with st.form("staff_signin_form"):
                login_username = st.text_input("아이디")
                pw = st.text_input("비밀번호", type="password")
                submit = st.form_submit_button("로그인", use_container_width=True)
            if submit:
                if not login_username.strip():
                    st.error("아이디를 입력해주세요.")
                else:
                    ok, msg = staff_signin(login_username.strip(), pw)
                    if ok:
                        reset_login_steps()
                        go("마이페이지"); st.rerun()
                    else:
                        st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 마이페이지
# ----------------------------------------------------------------------
def page_mypage():
    user = current_user()
    if user is None:
        if ss.get("current_user_id"):
            st.error("로그인은 되어 있지만 프로필 정보를 불러오지 못했습니다.")
            if ss.get("last_profile_error"):
                st.caption(f"상세: {ss.last_profile_error}")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("다시 시도"):
                    ss.profile_cache = None
                    st.rerun()
            with c2:
                if st.button("로그아웃 후 다시 로그인"):
                    logout(); st.rerun()
        else:
            st.warning("로그인이 필요합니다. 우측 상단 ☰ 메뉴에서 학생/교직원 인증을 진행해주세요.")
            if st.button("로그인 / 인증 하러 가기"):
                go("로그인"); st.rerun()
        render_footer()
        return

    st.markdown('<div class="bk-section-title">👤 마이페이지</div>', unsafe_allow_html=True)

    role_menus = {
        "학생": ["내 정보", "신청 내역", "시간표", "설문 참여 내역", "알림", "개인정보 설정", "로그아웃"],
        "교직원": ["내 정보", "교직원 전용 기능", "시간표", "알림", "개인정보 설정", "로그아웃"],
    }
    menu = role_menus.get(user["identity"], [])
    if user["is_admin"]:
        menu = ["👑 관리자 페이지"] + menu

    st.markdown('<div class="bk-card">', unsafe_allow_html=True)
    st.markdown(f"### {'👑' if user['is_admin'] else ('🎓' if user['identity']=='학생' else '🧑‍🏫')} {user['name']}")
    if user.get("student_no"):
        id_line = f"학번 {user['student_no']}"
    elif user.get("staff_username"):
        id_line = f"아이디 {user['staff_username']}"
    else:
        id_line = f"인증코드 {user.get('staff_code','-')}"
    st.write(f"**신분**: {user['identity']} ({id_line})  ·  **관리자 권한**: {'있음 👑' if user['is_admin'] else '없음'}")
    st.markdown("---")
    mcols = st.columns(3)
    for i, m in enumerate(menu):
        with mcols[i % 3]:
            st.markdown(f"<div class='bk-chip' style='margin-bottom:8px;'>{m}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if user["is_admin"]:
        st.write("")
        if st.button("👑 관리자 페이지로 이동"):
            go("관리자 페이지"); st.rerun()

    render_footer()


# ----------------------------------------------------------------------
# 페이지 : 관리자 페이지
# ----------------------------------------------------------------------
def page_admin():
    st.markdown('<div class="bk-section-title">👑 관리자 페이지</div>', unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:{MUTED};margin-bottom:10px;'>※ 관리자 권한 부여/회수, 인증코드 발급은 서비스 키(SUPABASE_SERVICE_KEY)가 설정되어 있어야 동작합니다.</div>",
        unsafe_allow_html=True,
    )
    admin_client = get_admin_client()
    if admin_client is None:
        st.warning("`secrets.toml` 에 `SUPABASE_SERVICE_KEY` 가 없어 일부 관리 기능(권한 부여/회수, 인증코드 발급, 공지/부스/프로그램/시간표 등록·수정·삭제)이 비활성화되어 있습니다.")

    tabs = st.tabs(["🧑‍💻 사용자 관리", "🔑 권한 관리", "🔒 인증코드 관리"])

    with tabs[0]:
        st.markdown('<div class="bk-card">', unsafe_allow_html=True)
        st.subheader("사용자 목록")
        client = get_user_client()
        try:
            res = client.table("profiles").select(
                "id,name,identity,is_admin,student_no,staff_code,staff_username"
            ).execute()
            users = res.data or []
        except Exception as e:
            st.error(_friendly_db_error(e))
            users = []
        if not users:
            st.info("등록된 사용자가 없습니다.")
        else:
            rows = [{"ID": u["id"], "이름": u["name"], "신분": u["identity"],
                     "학번/아이디": u.get("student_no") or u.get("staff_username") or "-",
                     "관리자": "✅" if u["is_admin"] else ""} for u in users]
            st.dataframe(rows, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[1]:
        st.markdown('<div class="bk-card">', unsafe_allow_html=True)
        st.subheader("관리자 권한 부여 / 회수")
        client = get_user_client()
        try:
            res = client.table("profiles").select("id,name,identity").execute()
            users = res.data or []
        except Exception as e:
            st.error(_friendly_db_error(e))
            users = []
        if not users:
            st.info("등록된 사용자가 없습니다.")
        elif admin_client is None:
            st.info("SUPABASE_SERVICE_KEY가 설정되면 이 기능을 사용할 수 있습니다.")
        else:
            target = st.selectbox("대상 사용자", [u["id"] for u in users],
                                   format_func=lambda uid: next(f"{u['name']} ({u['identity']})" for u in users if u["id"] == uid))
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👑 관리자 권한 부여"):
                    admin_client.table("profiles").update({"is_admin": True}).eq("id", target).execute()
                    st.success("관리자 권한을 부여했습니다."); st.rerun()
            with c2:
                if st.button("🚫 관리자 권한 회수"):
                    admin_client.table("profiles").update({"is_admin": False}).eq("id", target).execute()
                    st.success("관리자 권한을 회수했습니다."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown('<div class="bk-card">', unsafe_allow_html=True)
        st.subheader("교직원 인증코드 목록")
        client = get_user_client()
        try:
            res = client.table("staff_codes").select("*").execute()
            codes = res.data or []
        except Exception as e:
            st.error(_friendly_db_error(e))
            codes = []

        rows = [{"인증코드": c["code"], "담당자(사전등록)": c.get("name") or "-",
                 "상태": "활성" if c["active"] else "비활성",
                 "사용여부": "사용됨" if c["used_by"] else "미사용"} for c in codes]
        st.dataframe(rows, use_container_width=True)

        if admin_client is None:
            st.info("SUPABASE_SERVICE_KEY가 설정되면 인증코드 발급/비활성화를 사용할 수 있습니다.")
        else:
            import string
            st.markdown("**새 인증코드 발급**")
            with st.form("staff_code_new_form"):
                new_code_name = st.text_input("담당 선생님 이름", placeholder="예: 김철수")
                gen_submit = st.form_submit_button("➕ 새 인증코드 생성", use_container_width=True)
            if gen_submit:
                if not new_code_name.strip():
                    st.error("담당 선생님 이름을 입력해주세요. 최초 등록 시 이 이름이 자동으로 사용됩니다.")
                else:
                    new_code = "BK26-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
                    admin_client.table("staff_codes").insert(
                        {"code": new_code, "name": new_code_name.strip(), "active": True}
                    ).execute()
                    st.success(f"새 인증코드: {new_code} (담당: {new_code_name.strip()})"); st.rerun()
            if codes:
                target_code = st.selectbox("비활성화할 인증코드", ["선택 안함"] + [c["code"] for c in codes])
                if target_code != "선택 안함" and st.button("인증코드 비활성화"):
                    admin_client.table("staff_codes").update({"active": False}).eq("code", target_code).execute()
                    st.success("비활성화했습니다."); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.caption("📢 공지사항/부스/프로그램/시간표 등록·수정·삭제는 각각의 메뉴 화면에서 직접 할 수 있습니다 "
               "(각 카드/항목 안에서 수정·삭제, 우측 하단 + 버튼으로 신규 등록).")

    render_footer()


# ----------------------------------------------------------------------
# 푸터
# ----------------------------------------------------------------------
def render_footer():
    st.markdown(
        f"""
        <div class="bk-footer">
            <b>📮 문의 및 안내</b><br>
            📞 {ss.site_info['phone']} &nbsp;|&nbsp; ✉️ {ss.site_info['email']} &nbsp;|&nbsp; 🕒 {ss.site_info['hours']}<br>
            🏫 경복고등학교 학생회
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# 라우팅
# ----------------------------------------------------------------------
def main():
    handle_nav_query_param()
    render_topbar_and_drawer()

    routes = {
        "메인": page_main, "프로그램": page_programs,
        "시간표": page_schedule, "부스 정보": page_booths, "오시는 길": page_directions,
        "공지사항": page_notices, "FAQ": page_faq, "랜덤 추천": page_random, "인사말": page_greeting,
        "디지털 방문증": page_visitor_pass,
        "로그인": page_login, "마이페이지": page_mypage, "관리자 페이지": page_admin,
        "부스 등록": page_booth_add, "공지사항 등록": page_notice_add,
        "프로그램 등록": page_program_add, "시간표 등록": page_schedule_add,
    }

    if ss.page == "마이페이지" and current_user() is None and not ss.get("current_user_id"):
        st.warning("로그인이 필요합니다."); return
    if ss.page == "관리자 페이지" and not is_admin():
        if ss.get("current_user_id") and current_user() is None:
            st.error("로그인은 되어 있지만 프로필 정보를 불러오지 못해 관리자 권한을 확인할 수 없습니다.")
            if ss.get("last_profile_error"):
                st.caption(f"상세: {ss.last_profile_error}")
        else:
            st.error("관리자 권한이 없습니다.")
        return

    routes.get(ss.page, page_main)()


if __name__ == "__main__":
    main()
