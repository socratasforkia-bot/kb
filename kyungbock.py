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
LOGO_SVG_BASE64 = "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0NjYgNDY1IiB3aWR0aD0iNDY2IiBoZWlnaHQ9IjQ2NSI+CjxnIGZpbGw9IiMwQjYzQTciPgo8cGF0aCBkPSJNIDIwMiw0NTQgMjAzLDQ1MyAyMDQsNDU0IDIwOSw0NTQgMjEwLDQ1NiAyMDksNDU3IDIwNSw0NTcgMjAzLDQ1NiBaIi8+CjxwYXRoIGQ9Ik0gMTYzLDQ0OSAxNjUsNDQ3IDE2Nyw0NDcgMTY4LDQ0OCAxNjYsNDUwIDE2NCw0NTAgWiIvPgo8cGF0aCBkPSJNIDE1Nyw0NDMgMTYwLDQ0NSAxNTgsNDQ4IDE1Niw0NDYgMTU2LDQ0NCBaIi8+CjxwYXRoIGQ9Ik0gMTkwLDQ0MiAxOTAsNDQ3IDE4OSw0NDggMTg5LDQ1NSAxODgsNDU2IDE4OCw0NjEgMTkxLDQ2MSAxOTMsNDYyIDE5Myw0NjAgMTk0LDQ1OSAxOTQsNDUxIDE5NSw0NTAgMTk1LDQ0NyAxOTcsNDQ2IDE5OCw0NDcgMjE1LDQ0OCAyMTksNDUwIDIxOSw0NTYgMjE3LDQ1OSAyMTUsNDU5IDIxNCw0NTggMjE1LDQ1NiAyMTUsNDUxIDIxNCw0NTAgMjAzLDQ1MCAyMDIsNDQ5IDE5OCw0NDkgMTk4LDQ1MyAxOTcsNDU0IDE5Nyw0NTkgMTk4LDQ2MCAyMDcsNDYwIDIwOCw0NjEgMjE0LDQ2MSAyMTUsNDU5IDIxNiw0NjAgMjE2LDQ2NCAyMjEsNDY0IDIyMyw0NjIgMjIzLDQ1OSAyMjQsNDU4IDIyNCw0NTEgMjI1LDQ1MCAyMjUsNDQ2IDIyNCw0NDUgMjE2LDQ0NSAyMTUsNDQ0IDIwNiw0NDQgMjA1LDQ0MyAxOTcsNDQzIDE5Niw0NDIgWiIvPgo8cGF0aCBkPSJNIDE2OCw0NDAgMTcwLDQ0MSAxNzAsNDQzIDE2OSw0NDQgMTY4LDQ0NCAxNjYsNDQyIFoiLz4KPHBhdGggZD0iTSAxNjAsNDM3IDE2Miw0MzcgMTYzLDQzOCAxNjEsNDQxIDE1OCw0MzkgWiIvPgo8cGF0aCBkPSJNIDIwMiw0MzUgMjAzLDQzNCAyMDcsNDM0IDIwOCw0MzUgMjE0LDQzNSAyMTUsNDM2IDIxMyw0MzggMjA4LDQzOCAyMDcsNDM3IDIwMyw0MzcgWiIvPgo8cGF0aCBkPSJNIDE5Nyw0MzAgMTk3LDQzNyAxOTYsNDM4IDE5Niw0NDAgMjAxLDQ0MCAyMDIsNDQxIDIwOSw0NDEgMjEwLDQ0MiAyMTgsNDQyIDIxOSw0NDMgMjIwLDQ0MiAyMjAsNDM0IDIyMSw0MzMgMjIwLDQzMiAyMDYsNDMxIDIwNSw0MzAgWiIvPgo8cGF0aCBkPSJNIDI1Miw0MzAgMjU0LDQyOCAyNTYsNDI4IDI1Nyw0MjkgMjU2LDQzMCAyNTcsNDMxIDI1Niw0MzIgMjU0LDQzMiBaIi8+CjxwYXRoIGQ9Ik0gMjk3LDQyOCAyOTksNDI3IDMwMCw0MjUgMzAyLDQyNyAzMDAsNDI5IDI5OCw0MjkgWiIvPgo8cGF0aCBkPSJNIDE2NSw0MjYgMTY2LDQyNSAxNzEsNDI2IDE3Myw0MjggMTczLDQyOSAxNzEsNDMwIDE2OCw0MjggMTY2LDQyOCBaIi8+CjxwYXRoIGQ9Ik0gMzA3LDQyMyAzMDksNDI1IDMwNSw0MjcgMzA0LDQyNiBaIi8+CjxwYXRoIGQ9Ik0gMjkzLDQyNCAyOTUsNDIyIDI5Nyw0MjIgMjk4LDQyMyAyOTUsNDI1IFoiLz4KPHBhdGggZD0iTSAzMTcsNDIxIDMxNyw0MjIgMzE0LDQyNCAzMTIsNDI0IDMxMSw0MjUgMzEwLDQyNCAzMTAsNDIzIDMxMiw0MjEgMzE0LDQyMSAzMTUsNDIwIFoiLz4KPHBhdGggZD0iTSAyNzYsNDIyIDI2Niw0MjMgMjY1LDQyMSAyNjAsNDIxIDI2MCw0MjQgMjU3LDQyOSAyNTYsNDI4IDI1Niw0MjUgMjQ3LDQyNSAyNDYsNDIzIDI0NCw0MjMgMjQzLDQyMiAyNDEsNDIzIDI0MSw0MjUgMjM3LDQzMiAyMzksNDM0IDI0MSw0MzQgMjQ0LDQzMCAyNDYsNDMwIDI0OCw0MzQgMjQ5LDQzMyAyNTIsNDMzIDI1Myw0MzIgMjU0LDQzMyAyNTQsNDM1IDI1Myw0MzYgMjQ3LDQzNiAyNDYsNDM3IDI0Myw0MzcgMjQzLDQzOSAyNDQsNDQxIDI0Nyw0NDEgMjQ4LDQ0MCAyNTQsNDQwIDI1NSw0NDEgMjUzLDQ0MyAyNDUsNDQzIDI0NCw0NDQgMjQwLDQ0NCAyNDAsNDQ4IDI0Nyw0NDggMjQ4LDQ0NyAyNjIsNDQ2IDI2Myw0NDUgMjY2LDQ0NSAyNjcsNDQ2IDI2Niw0NDggMjYxLDQ0OCAyNjAsNDQ5IDI1Myw0NDkgMjUyLDQ1MCAyNDQsNDUwIDI0Myw0NTEgMjQzLDQ1NSAyNDcsNDU1IDI1Myw0NjMgMjU3LDQ2MCAyNTcsNDU5IDI1Myw0NTUgMjU2LDQ1MyAyNjQsNDUzIDI2NSw0NTIgMjY3LDQ1MiAyNjgsNDUzIDI2OCw0NTUgMjY2LDQ1NyAyNjQsNDU3IDI2NCw0NTkgMjY2LDQ2MiAyNzAsNDYyIDI3NCw0NTcgMjc0LDQ1NCAyNzMsNDUzIDI3Niw0NTEgMjc4LDQ1MSAyNzgsNDQ3IDI3Myw0NDcgMjcyLDQ0NiAyNzMsNDQ0IDI3OCw0NDQgMjc4LDQ0MCAyNzAsNDQwIDI2OSw0NDEgMjYyLDQ0MSAyNjEsNDQwIDI2NCw0MzggMjcwLDQzOCAyNzEsNDM3IDI3Myw0MzcgMjczLDQzNCAyNzIsNDMzIDI3MSw0MzQgMjY1LDQzNCAyNjQsNDM1IDI2Miw0MzUgMjYxLDQzNCAyNjEsNDMyIDI2NSw0MjcgMjY3LDQyNyAyNjgsNDI4IDI2OCw0MzEgMjczLDQzMCAyNzMsNDI3IDI3Niw0MjUgWiIvPgo8cGF0aCBkPSJNIDI5Nyw0MjAgMjk5LDQxOSAzMDAsNDIwIDI5OSw0MjEgMzAyLDQyMyAzMDAsNDI1IDI5OSw0MjUgMjk3LDQyMiBaIi8+CjxwYXRoIGQ9Ik0gMTkxLDQyNSAxOTEsNDI3IDE5OCw0MjcgMTk5LDQyOCAyMDYsNDI4IDIwNyw0MjkgMjE1LDQyOSAyMTYsNDMwIDIyMyw0MzAgMjI0LDQzMSAyMjcsNDMxIDIyOCw0MzAgMjI4LDQyNyAyMjYsNDI3IDIyNSw0MjYgMjE3LDQyNiAyMTYsNDI1IDIxNCw0MjUgMjEzLDQyNCAyMTMsNDIxIDIwOSw0MjEgMjA4LDQyMCAyMDcsNDIwIDIwNyw0MjMgMjA2LDQyNCAxOTgsNDI0IDE5Nyw0MjMgMTkyLDQyMyBaIi8+CjxwYXRoIGQ9Ik0gMTYzLDQxOSAxNjEsNDIyIDE2MSw0MjQgMTU5LDQyNyAxNTksNDI5IDE2Myw0MzAgMTY0LDQzMSAxNjYsNDMxIDE2Nyw0MzIgMTY5LDQzMiAxNzUsNDM1IDE3Nyw0MzIgMTc3LDQzMCAxNzksNDI3IDE3OSw0MjUgWiIvPgo8cGF0aCBkPSJNIDI5MSw0MTkgMjkzLDQxNyAyOTUsNDE3IDI5Niw0MTggMjkzLDQyMCBaIi8+CjxwYXRoIGQ9Ik0gMzAxLDQxOCAzMDMsNDE2IDMwNSw0MTYgMzA2LDQxNyAzMDQsNDE5IDMwMiw0MTkgWiIvPgo8cGF0aCBkPSJNIDMxNCw0MTUgMzE1LDQxNiAzMTMsNDE4IDMxMiw0MTggMzEyLDQyMCAzMTAsNDIxIDMwOSw0MjAgMzA5LDQxNyAzMTAsNDE2IFoiLz4KPHBhdGggZD0iTSAxNjIsNDE0IDE2Miw0MTYgMTY2LDQxOCAxNzEsNDE5IDE3NCw0MjEgMTc5LDQyMiAxODIsNDI0IDE4NCw0MjAgMTgzLDQxOSAxNzgsNDE4IDE3NSw0MTYgMTczLDQxNiAxNzIsNDE1IDE3MCw0MTUgMTY2LDQxMyAxNjMsNDEzIFoiLz4KPHBhdGggZD0iTSAxNDMsNDEzIDE0MSw0MTcgMTQyLDQxOCAxNDYsNDE5IDE0Nyw0MjEgMTQ1LDQyMiAxNDEsNDIwIDEzOSw0MjQgMTM5LDQyNiAxMzUsNDM0IDEzMyw0MzYgMTMzLDQzOCAxMzQsNDM4IDEzNiw0NDAgMTQwLDQzNCAxNDEsNDM1IDE0MSw0MzcgMTM5LDQ0MCAxMzgsNDQ1IDE0Miw0NDcgMTQzLDQ0MyAxNDQsNDQyIDE0NCw0NDAgMTQ1LDQzOSAxNDgsNDQxIDE1MCw0NDEgMTUyLDQzNyAxNTMsNDM4IDE1Myw0NDAgMTUxLDQ0MyAxNTEsNDQ1IDE0OSw0NDkgMTUzLDQ1MCAxNTQsNDUxIDE1Niw0NTEgMTU3LDQ1MiAxNTksNDUyIDE2MCw0NTMgMTYyLDQ1MyAxNjMsNDU0IDE2NSw0NTQgMTY4LDQ1NiAxNzAsNDU2IDE3MSw0NTIgMTczLDQ0OSAxNzQsNDQ0IDE3Niw0NDEgMTc2LDQzOCAxNzIsNDM3IDE2OSw0MzUgMTY0LDQzNCAxNTgsNDMxIDE1Niw0MzEgMTU1LDQzMiAxNTQsNDMwIDE1Niw0MjYgMTUyLDQyNSAxNTEsNDI3IDE1MCw0MjYgMTUwLDQyNCAxNTIsNDIxIDE1Niw0MjMgMTU4LDQyMyAxNTksNDE5IDE1OCw0MTggMTU2LDQxOCAxNTAsNDE1IDE0OCw0MTUgMTQ3LDQxNCBaIi8+CjxwYXRoIGQ9Ik0gMTAwLDQxMiAxMDMsNDE1IDEwMyw0MTYgMTAxLDQxOCAxMDAsNDE4IDk4LDQxNiBaIi8+CjxwYXRoIGQ9Ik0gMzEzLDQxMSAzMTMsNDEyIDMxMCw0MTQgMzA4LDQxNCAzMDYsNDEyIDMwNyw0MTEgMzExLDQxMSAzMTIsNDEwIFoiLz4KPHBhdGggZD0iTSAxMDUsNDExIDEwNyw0MTAgMTEzLDQxNSAxMTEsNDE2IFoiLz4KPHBhdGggZD0iTSAxMDIsNDA4IDEwMyw0MDcgMTA2LDQxMCAxMDQsNDExIDEwMiw0MDkgWiIvPgo8cGF0aCBkPSJNIDE0Nyw0MDYgMTQ2LDQwOCAxNDYsNDExIDE0OCw0MTEgMTUxLDQxMyAxNTksNDE1IDE2MCw0MTEgWiIvPgo8cGF0aCBkPSJNIDMxNyw0MDUgMzEzLDQwNiAzMTIsNDA3IDMxMCw0MDcgMzA4LDQwOCAzMDcsNDEwIDMwMyw0MTAgMzAxLDQxMiAzMDAsNDExIDI5OCw0MTEgMjk2LDQxNSAyOTQsNDEzIDI5Myw0MTMgMjg1LDQxNyAyODgsNDIzIDI4OCw0MjUgMjkxLDQzMCAyOTEsNDMxIDI4OSw0MzMgMjkxLDQ0MSAyOTcsNDM5IDI5NSw0MzYgMjk3LDQzNCAyOTksNDM1IDMwMCw0MzkgMzA0LDQzNyAzMDYsNDM3IDMwNyw0MzYgMzA5LDQzNiAzMTAsNDM3IDMwNSw0NDEgMzAzLDQ0MSAzMDIsNDQyIDMwMCw0NDIgMjk5LDQ0MyAyOTUsNDQ0IDI5NCw0NDUgMjk1LDQ0NiAyOTUsNDQ4IDI5Nyw0NDggMjk4LDQ0NyAzMDAsNDQ3IDMwMSw0NDYgMzAzLDQ0NiAzMDYsNDQ0IDMxMCw0NDMgMzExLDQ0NSAzMDksNDQ3IDMwNyw0NDcgMzEwLDQ1MSAzMTAsNDUyIDMxMSw0NTEgMzEzLDQ1MSAzMTUsNDUwIDMxOCw0NDYgMzE3LDQ0MiAzMTYsNDQxIDMxNyw0NDAgMzMxLDQzNSAzMjksNDMxIDMyMyw0MzQgMzIxLDQzNCAzMTgsNDM2IDMxNiw0MzUgMzE5LDQzMCAzMTksNDI4IDMxNyw0MjcgMzE4LDQyNiAzMjEsNDI1IDMyMyw0MjkgMzI0LDQyOCAzMjgsNDI3IDMyNyw0MjMgMzI2LDQyMiAzMjYsNDIwIDMyNSw0MTkgMzIzLDQyMCAzMjEsNDE5IDMyMSw0MTcgMzIwLDQxNiAzMjAsNDE0IDMxOSw0MTMgWiIvPgo8cGF0aCBkPSJNIDM0NywzOTYgMzQ4LDM5NyAzNDgsMzk5IDM0Niw0MDMgMzQ2LDQwNiAzNDgsNDA2IDM0OSw0MDcgMzUyLDQwNiAzNTYsNDEwIDM1OSw0MTEgMzYxLDQxMyAzNTUsNDI1IDM1Myw0MjMgMzUxLDQxOSAzNDgsNDE2IDM0OCw0MTUgMzUwLDQxNCAzNTAsNDA5IDM0Nyw0MDkgMzQzLDQwNyAzNDEsNDA1IDM0MSw0MDMgMzQyLDQwMiAzNDEsNDAwIDM0NSwzOTggWiIvPgo8cGF0aCBkPSJNIDM0OCwzOTYgMzU1LDM5MSAzNTYsMzkyIDM1NiwzOTUgMzU3LDM5NiAzNjIsMzk2IDM2MywzOTcgMzYxLDM5OCAzNjEsNDAyIDM2Miw0MDMgMzYyLDQwNSAzNjAsNDA2IDM1NCw0MDIgMzUzLDQwNCAzNTIsNDAzIDM1MiwzOTcgMzQ5LDM5NyBaIi8+CjxwYXRoIGQ9Ik0gMTEzLDM4NCAxMDUsMzk1IDEwNiwzOTYgMTA1LDM5NyAxMDQsMzk3IDEwMCwzOTQgOTgsMzk0IDk3LDM5NyA5OCwzOTcgMTAzLDQwMSAxMDIsNDAyIDEwMCw0MDEgOTksNDAyIDk5LDQwMyA5NSw0MDggOTYsNDEwIDk0LDQxMSA5Myw0MTAgODksNDEwIDg3LDQwOSA4Niw0MTQgODgsNDE1IDk3LDQxNSA5OCw0MTYgOTcsNDIyIDEwMSw0MjQgMTA0LDQyNCAxMDgsNDE5IDExMCw0MTkgMTExLDQyMCAxMTAsNDIxIDExMCw0MjUgMTExLDQyNiAxMTEsNDI4IDExNCw0MzMgMTE2LDQzMyAxMTcsNDMyIDExOSw0MzIgMTE5LDQzMSAxMTcsNDI5IDExNSw0MjUgMTE2LDQyNCAxMTgsNDI0IDExOCw0MjMgMTIzLDQxNyAxMjIsNDE2IDEyNCw0MTUgMTI3LDQxOCAxMjgsNDE4IDEzMCw0MTYgMTMwLDQxNCAxMjksNDE0IDEyNSw0MTEgMTI4LDQwOCAxMjgsNDA3IDEzMCw0MDUgMTM0LDM5OCAxMjQsMzkxIDEyMywzOTEgMTIxLDM4OSAxMjAsMzg5IDExOCwzODcgMTE3LDM4NyAxMTQsMzg0IFoiLz4KPHBhdGggZD0iTSAzNjEsMzgyIDM1OSwzODIgMzUyLDM4NyAzNTAsMzg0IDM0NiwzODUgMzQ1LDM4NiAzNDUsMzg4IDM0NywzOTAgMzQ0LDM5MyAzNDAsMzk1IDM0MCwzOTggMzM5LDM5OSAzMzcsMzk5IDMzNCwzOTUgMzMyLDM5NSAzMjksMzk3IDMyOSwzOTggMzMyLDQwMSAzMzIsNDAzIDMzMCw0MDUgMzMwLDQwNiAzMzIsNDA4IDMzMiw0MDkgMzM0LDQwOCAzMzYsNDA4IDMzNyw0MDkgMzM4LDQxNSAzMzksNDE2IDMzOSw0MjMgMzQxLDQyNCAzNDQsNDI0IDM0NCw0MjEgMzQ1LDQyMCAzNTMsNDMxIDM1NSw0MzEgMzU3LDQyOSAzNTUsNDI1IDM1Niw0MjQgMzYwLDQyNiAzNjIsNDI1IDM2NCw0MjEgMzY0LDQxOSAzNjYsNDE2IDM2Niw0MTQgMzY3LDQxMyAzODAsNDEzIDM4MCw0MDcgMzc1LDQwNyAzNzQsNDA4IDM2OCw0MDggMzY3LDQwNyAzNjcsNDAyIDM2Niw0MDEgMzY2LDM5OCAzNjUsMzk3IDM2NywzOTUgMzY3LDM5MSAzNjYsMzkwIDM2MywzOTAgMzYyLDM5MSAzNTgsMzkxIDM1NywzOTAgMzYzLDM4NSBaIi8+CjxwYXRoIGQ9Ik0gMjE3LDM2OCAyMjAsMzY4IDIyMiwzNzAgMjIyLDM3MyAyMjMsMzc0IDIyMiwzNzUgMjIyLDM3NyAyMTksMzgwIDIxNywzODAgMjE0LDM3NyAyMTQsMzc1IDIxMywzNzQgMjE0LDM3MSBaIi8+CjxwYXRoIGQ9Ik0gMjc2LDM2NCAyNzEsMzY4IDI3MCwzNjggMjY3LDM3MSAyNjYsMzcxIDI2NiwzNzIgMjY5LDM3NSAyNjksMzc2IDI3MCwzNzYgMjc0LDM3MiAyNzUsMzczIDI3NSwzOTYgMjgyLDM5NiAyODIsMzY0IFoiLz4KPHBhdGggZD0iTSAxODgsMzY0IDE4MywzNjkgMTgyLDM2OSAxODAsMzcxIDE4MCwzNzIgMTgzLDM3NiAxODYsMzczIDE4OCwzNzQgMTg4LDM5NiAxOTUsMzk2IDE5NSwzNjQgWiIvPgo8cGF0aCBkPSJNIDIzOSwzNjYgMjM5LDM3MCAyNDIsMzcwIDI0MywzNjkgMjUwLDM2OSAyNTIsMzcxIDI1MiwzNzUgMjQ5LDM3OSAyNDksMzgwIDIzOCwzOTEgMjM4LDM5NiAyNjAsMzk2IDI2MCwzOTEgMjQ5LDM5MSAyNDgsMzkwIDI1MywzODUgMjUzLDM4NCAyNTYsMzgxIDI1OCwzNzcgMjU5LDM3MSAyNTgsMzcwIDI1NywzNjYgMjUyLDM2MyAyNDYsMzYzIDI0NSwzNjQgMjQyLDM2NCBaIi8+CjxwYXRoIGQ9Ik0gMjE1LDM2MyAyMTEsMzY1IDIwOCwzNjkgMjA4LDM3MyAyMDcsMzc0IDIwOCwzNzYgMjA4LDM3OSAyMTIsMzg0IDIxOSwzODUgMjIyLDM4MyAyMjMsMzg0IDIyMywzODYgMjE5LDM5MSAyMTYsMzkxIDIxNSwzOTIgMjEzLDM5MSAyMTAsMzkxIDIwOSwzOTMgMjA5LDM5NiAyMTEsMzk2IDIxMiwzOTcgMjE5LDM5NyAyMjAsMzk2IDIyMiwzOTYgMjI2LDM5MiAyMjgsMzg4IDIyOCwzODUgMjI5LDM4NCAyMjksMzczIDIyNSwzNjUgMjIxLDM2MyBaIi8+CjxwYXRoIGQ9Ik0gMzc4LDM2MyAzNzcsMzY3IDM3NiwzNjggMzc2LDM3NyAzNzcsMzc4IDM3OCwzODIgMzg1LDM4OSAzODksMzkxIDQwMCwzOTEgNDAxLDM5MCA0MDUsMzg5IDQwOSwzODYgNDA5LDM4NCA0MDEsMzgwIDM5MSwzODAgMzg3LDM4MiAzODYsMzgxIDM4NywzNzkgMzg3LDM3NiAzODgsMzc1IDM4OCwzNzAgMzg3LDM2OSAzODcsMzY3IDM4NSwzNjMgMzgyLDM2MCAzODEsMzYwIFoiLz4KPHBhdGggZD0iTSA4NCwzNjAgODIsMzYwIDgwLDM2MiA3NywzNjggNzcsMzc3IDc5LDM4MSA3OCwzODMgNzMsMzgwIDYzLDM4MCA2MiwzODEgNTgsMzgyIDU1LDM4NSA1OCwzODggNjQsMzkxIDc1LDM5MSA4MSwzODggODUsMzg0IDg3LDM4MCA4NywzNzggODgsMzc3IDg4LDM2NyBaIi8+CjxwYXRoIGQ9Ik0gMzk0LDM0MiAzOTIsMzQ2IDM5MiwzNDkgMzkxLDM1MCAzOTEsMzU2IDM5MiwzNTcgMzkyLDM2MCAzOTcsMzY3IDQwNCwzNzEgNDEyLDM3MiA0MTMsMzcxIDQxNywzNzEgNDIxLDM2OSA0MjYsMzY0IDQyNiwzNjMgNDIwLDM2MCA0MTAsMzYwIDQwOSwzNjEgNDA1LDM2MiA0MDMsMzY0IDQwMiwzNjMgNDAzLDM2MSA0MDMsMzUyIDQwMiwzNTEgNDAyLDM0OSA0MDAsMzQ1IDM5NiwzNDEgWiIvPgo8cGF0aCBkPSJNIDcwLDM0MiA2OCwzNDEgNjUsMzQ0IDY1LDM0NSA2MiwzNDkgNjIsMzUxIDYxLDM1MiA2MSwzNjAgNjIsMzYyIDYxLDM2MyA1NywzNjEgNTUsMzYxIDU0LDM2MCA0NCwzNjAgNDAsMzYyIDM4LDM2NCA0NSwzNzAgNTEsMzcxIDUyLDM3MiA2MCwzNzEgNjYsMzY4IDcxLDM2MiA3MiwzNTggNzMsMzU3IDczLDM0OCBaIi8+CjxwYXRoIGQ9Ik0gNDA2LDMyMyA0MDUsMzI3IDQwNCwzMjggNDA0LDMzNCA0MDUsMzM1IDQwNSwzMzggNDA3LDM0MiA0MTMsMzQ4IDQxNywzNDkgNDE4LDM1MCA0MjksMzUwIDQzNiwzNDYgNDM5LDM0MyA0NDAsMzQwIDQzNiwzMzggNDI2LDMzOCA0MjUsMzM5IDQyMSwzNDAgNDE3LDM0MyA0MTYsMzQyIDQxNywzMzYgNDE2LDMzNSA0MTYsMzMyIDQxNCwzMjggNDExLDMyNSA0MTEsMzI0IDQxMCwzMjQgNDA4LDMyMiBaIi8+CjxwYXRoIGQ9Ik0gNTgsMzIzIDU2LDMyMiA1MSwzMjYgNDksMzMwIDQ5LDMzMiA0OCwzMzMgNDgsMzM2IDQ3LDMzNyA0NywzMzkgNDgsMzQwIDQ4LDM0MiA0NywzNDMgNDIsMzM5IDM5LDMzOSAzOCwzMzggMjgsMzM4IDI0LDM0MCAyNSwzNDIgMzEsMzQ4IDM1LDM0OSAzNiwzNTAgNDYsMzUwIDQ3LDM0OSA1MSwzNDggNTcsMzQyIDYwLDMzNiA2MCwzMjggNTksMzI3IFoiLz4KPHBhdGggZD0iTSA0MTYsMzAyIDQxNiwzMDUgNDE1LDMwNiA0MTUsMzExIDQxNiwzMTIgNDE2LDMxNSA0MTgsMzE5IDQyNCwzMjUgNDI2LDMyNiA0MjgsMzI2IDQyOSwzMjcgNDMzLDMyNyA0MzQsMzI4IDQ0MSwzMjcgNDQ1LDMyNSA0NTAsMzIwIDQ1MiwzMTYgNDUxLDMxNSA0NDgsMzE1IDQ0NywzMTQgNDQwLDMxNCA0MzksMzE1IDQzNSwzMTYgNDMwLDMyMCA0MjksMzE5IDQyOSwzMTUgNDI2LDMwOSA0MjYsMzA3IDQyMiwzMDMgNDE4LDMwMSBaIi8+CjxwYXRoIGQ9Ik0gNDksMzAyIDQ3LDMwMSA0MywzMDMgMzksMzA3IDM5LDMwOSAzNiwzMTUgMzYsMzE5IDM1LDMyMCAzMiwzMTcgMjgsMzE1IDI2LDMxNSAyNSwzMTQgMTgsMzE0IDE3LDMxNSAxNCwzMTUgMTMsMzE2IDE1LDMyMCAyMCwzMjUgMjQsMzI3IDMxLDMyOCAzMiwzMjcgMzYsMzI3IDM3LDMyNiAzOSwzMjYgNDEsMzI1IDQ3LDMxOSA0OSwzMTUgNDksMzEyIDUwLDMxMSA1MCwzMDYgNDksMzA1IFoiLz4KPHBhdGggZD0iTSAyOTcsMjkyIDI5OCwyOTEgMzA2LDI5MSAzMDcsMjkyIDMwNywzMDEgMzA2LDMwMiAyOTgsMzAyIDI5NywzMDEgWiIvPgo8cGF0aCBkPSJNIDI2MCwyOTIgMjYxLDI5MSAyNzAsMjkxIDI3MSwyOTIgMjcxLDMwMSAyNzAsMzAyIDI2MSwzMDIgMjYwLDMwMSBaIi8+CjxwYXRoIGQ9Ik0gNDIzLDI4MCA0MjMsMjkwIDQyNCwyOTEgNDI1LDI5NSA0MzEsMzAxIDQzNSwzMDIgNDM2LDMwMyA0NDAsMzAzIDQ0MSwzMDQgNDQ5LDMwMyA0NTMsMzAxIDQ1OCwyOTYgNDYwLDI5MiA0NjAsMjkwIDQ1OSwyODkgNDUwLDI4OSA0NDksMjkwIDQ0NSwyOTEgNDM5LDI5NyA0MzgsMjk5IDQzNywyOTggNDM3LDI5MSA0MzMsMjg0IDQzMiwyODQgNDI5LDI4MSA0MjUsMjc5IFoiLz4KPHBhdGggZD0iTSA0MiwyODAgNDAsMjc5IDMyLDI4NCAyOCwyOTEgMjgsMjk2IDI3LDI5NyAyNiwyOTcgMjAsMjkxIDE2LDI5MCAxNSwyODkgNiwyODkgNSwyOTAgNSwyOTIgNywyOTYgMTIsMzAxIDE2LDMwMyAxOSwzMDMgMjAsMzA0IDI5LDMwMyAzMCwzMDIgMzQsMzAxIDQwLDI5NSA0MSwyOTEgNDIsMjkwIFoiLz4KPHBhdGggZD0iTSAyOTcsMjU4IDI5OCwyNTcgMzA2LDI1NyAzMDcsMjU4IDMwNywyNjcgMzA2LDI2OCAyOTgsMjY4IDI5NywyNjcgWiIvPgo8cGF0aCBkPSJNIDI2MCwyNTggMjYxLDI1NyAyNzAsMjU3IDI3MSwyNTggMjcxLDI2NyAyNzAsMjY4IDI2MSwyNjggMjYwLDI2NyBaIi8+CjxwYXRoIGQ9Ik0gNDI4LDI1NyA0MjgsMjY2IDQzMCwyNzAgNDM1LDI3NiA0MzksMjc4IDQ0MiwyNzggNDQzLDI3OSA0NTIsMjc5IDQ1NSwyNzcgNDU3LDI3NyA0NjMsMjcxIDQ2NSwyNjcgNDY1LDI2MyA0NTcsMjYzIDQ1NiwyNjQgNDUyLDI2NSA0NDQsMjc0IDQ0MywyNzMgNDQzLDI2OSA0MzksMjYyIDQzMiwyNTcgWiIvPgo8cGF0aCBkPSJNIDM3LDI1NyAzNCwyNTcgMjgsMjYwIDI0LDI2NSAyMiwyNjkgMjIsMjcyIDIxLDI3MyAyMCwyNzMgMTksMjcxIDEzLDI2NSA5LDI2NCA4LDI2MyAwLDI2MyAwLDI2NyAyLDI3MSA4LDI3NyAxMCwyNzggMTIsMjc4IDEzLDI3OSAyMiwyNzkgMjMsMjc4IDI2LDI3OCAzMCwyNzYgMzUsMjcwIDM3LDI2NiBaIi8+CjxwYXRoIGQ9Ik0gMzQ5LDI0MSAzNDksMjU4IDQxNCwyNTggNDE0LDI1NiA0MTUsMjU1IDQxNSwyNDcgNDE2LDI0NiA0MTYsMjQxIFoiLz4KPHBhdGggZD0iTSA0OSwyNDEgNDksMjUyIDUwLDI1MyA1MCwyNTggMTE1LDI1OCAxMTUsMjQxIFoiLz4KPHBhdGggZD0iTSAyMzQsMjMzIDIzNCwzMjYgMjM1LDMyNyAzMzMsMzI3IDMzMywyMzMgWiIvPgo8cGF0aCBkPSJNIDQ0OSwyMzIgNDQ3LDIzMyA0NDcsMjM0IDQ0NCwyMzcgNDQzLDI0MSA0NDIsMjQyIDQ0MiwyNTEgNDQzLDI1MiA0NDMsMjU1IDQ0NiwyNTkgNDQ3LDI1OSA0NTEsMjU1IDQ1MywyNTEgNDUzLDI0OCA0NTQsMjQ3IDQ1MywyMzkgWiIvPgo8cGF0aCBkPSJNIDE2LDIzMiAxMiwyMzkgMTIsMjQxIDExLDI0MiAxMSwyNDcgMTIsMjQ4IDEyLDI1MSAxNCwyNTUgMTgsMjU5IDE5LDI1OSAyMywyNTEgMjMsMjQzIDIyLDI0MiAyMiwyMzkgMjEsMjM3IFoiLz4KPHBhdGggZD0iTSAzNDksMjE1IDM0OSwyMjQgNDE2LDIyNCA0MTYsMjIxIDQxNSwyMjAgNDE1LDIxNSBaIi8+CjxwYXRoIGQ9Ik0gNDksMjE1IDQ5LDIyNCAxMTUsMjI0IDExNSwyMTUgWiIvPgo8cGF0aCBkPSJNIDIwMCwxOTUgMjAwLDMyNyAyMjUsMzI3IDIyNSwxOTUgWiIvPgo8cGF0aCBkPSJNIDEzMSwxOTUgMTMxLDMyNyAxNTYsMzI3IDE1NiwxOTUgWiIvPgo8cGF0aCBkPSJNIDQ2NCwxOTEgNDU0LDE5MiA0NTMsMTkzIDQ0NywxOTMgNDQ2LDE5NCA0NDEsMTk0IDQ0MCwxOTUgNDM1LDE5NSA0MzQsMTk2IDQzMiwxOTYgNDMyLDE5OCA0MzMsMTk5IDQzMywyMDUgNDM0LDIwNiA0MzQsMjEwIDQzNSwyMTEgNDM2LDIxMCA0MzksMjEwIDQzOSwyMDcgNDM4LDIwNiA0MzgsMjAxIDQzOSwyMDAgNDQxLDIwMCA0NDIsMTk5IDQ0NywxOTkgNDQ4LDE5OCA0NTMsMTk4IDQ1NCwxOTcgNDU5LDE5NyA0NjAsMTk2IDQ2NCwxOTYgWiIvPgo8cGF0aCBkPSJNIDI2MCwxODcgMjYxLDE4NiAzMDYsMTg2IDMwNywxODcgMzA3LDE5NyAzMDYsMTk4IDI2MSwxOTggMjYwLDE5NyBaIi8+CjxwYXRoIGQ9Ik0gMywxODIgMiwxODggMTMsMTk4IDExLDE5OSAxMCwxOTggNCwxOTggMywxOTcgMSwxOTcgMCwxOTkgMCwyMDIgMiwyMDIgMywyMDMgOCwyMDMgOSwyMDQgMTQsMjA0IDE1LDIwNSAyMCwyMDUgMjEsMjA2IDI2LDIwNiAyNywyMDcgMzEsMjA3IDMyLDIwNSAzMiwyMDMgMzEsMjAyIDIxLDIwMSAyMCwxOTkgMzAsMTk0IDMyLDE5NCAzNCwxOTIgMzQsMTg4IDM1LDE4NyAzMSwxODggMjYsMTkxIDI0LDE5MSAxOSwxOTQgMTYsMTk0IDE0LDE5MyBaIi8+CjxwYXRoIGQ9Ik0gNDUyLDE2NCA0NTMsMTY2IDQ1MywxNjkgNDUyLDE3MSA0NDksMTc0IDQ0MywxNzcgNDM1LDE3NyA0MzEsMTc0IDQzMSwxNzEgNDMwLDE3MCA0MzEsMTY4IDQzNSwxNjQgNDM5LDE2MiA0NDQsMTYyIDQ0NSwxNjEgNDQ3LDE2MSA0NDgsMTYyIDQ1MCwxNjIgWiIvPgo8cGF0aCBkPSJNIDIzNCwxNjIgMjM0LDIyMiAzMzMsMjIyIDMzMywxNjEgMjM1LDE2MSBaIi8+CjxwYXRoIGQ9Ik0gMTMyLDE2MSAxMzEsMTYyIDEzMSwxODYgMTY1LDE4NiAxNjYsMTg3IDE2NiwzMjcgMTkxLDMyNyAxOTEsMTg3IDE5MiwxODYgMjI1LDE4NiAyMjUsMTYxIFoiLz4KPHBhdGggZD0iTSA0NTMsMTU4IDQ1MSwxNTcgNDQ3LDE1NyA0NDYsMTU2IDQ0NCwxNTYgNDQzLDE1NyA0MzgsMTU3IDQzNywxNTggNDM1LDE1OCA0MzEsMTYxIDQzMCwxNjEgNDI3LDE2NCA0MjYsMTY4IDQyNSwxNjkgNDI1LDE3MiA0MjYsMTczIDQyNywxNzcgNDMxLDE4MSA0MzMsMTgyIDQ0MywxODIgNDQ0LDE4MSA0NDcsMTgxIDQ1NCwxNzcgNDU4LDE3MSA0NTgsMTY1IDQ1NiwxNjEgWiIvPgo8cGF0aCBkPSJNIDEzLDE0OSAxMiwxNTQgMjIsMTYzIDIxLDE2NCAxNCwxNjQgMTMsMTY1IDgsMTY1IDYsMTY5IDYsMTcxIDgsMTcwIDE0LDE3MCAxNSwxNjkgMjksMTY4IDMwLDE2OSAzMiwxNjkgMzMsMTcwIDM1LDE3MCAzOSwxNzIgNDAsMTY4IDQxLDE2NyAyOSwxNjMgMjAsMTU0IDE5LDE1NCAxNCwxNDkgWiIvPgo8cGF0aCBkPSJNIDQzOSwxMzEgNDM5LDEzNSA0MzgsMTM3IDQzNSwxNDAgNDM0LDE0MCA0MzAsMTQzIDQyOCwxNDMgNDI3LDE0NCA0MjEsMTQ0IDQxNywxMzkgNDE3LDEzNiA0MTksMTM0IDQxOSwxMzMgNDI3LDEyOCA0MzQsMTI3IFoiLz4KPHBhdGggZD0iTSAyMzQsMTI3IDIzNCwxNTIgMzMzLDE1MiAzMzMsMTI3IFoiLz4KPHBhdGggZD0iTSAxMzEsMTI3IDEzMSwxNTIgMjI1LDE1MiAyMjUsMTI3IFoiLz4KPHBhdGggZD0iTSA0NDAsMTI0IDQzNiwxMjIgNDI5LDEyMiA0MjgsMTIzIDQyNSwxMjMgNDE4LDEyNyA0MTQsMTMxIDQxMiwxMzUgNDEyLDE0MCA0MTQsMTQ0IDQxOCwxNDggNDIwLDE0OSA0MjksMTQ5IDQzNywxNDUgNDQzLDEzOSA0NDQsMTM3IDQ0NCwxMzAgNDQyLDEyNiBaIi8+CjxwYXRoIGQ9Ik0gMjgsMTE4IDI2LDEyMSAyNywxMjMgNDcsMTMzIDQ5LDEzNiA0OSwxMzggNDcsMTQxIDQ1LDE0MiA0MiwxNDIgMjIsMTMyIDIwLDEzMyAxOSwxMzYgMzksMTQ2IDQxLDE0NiA0MiwxNDcgNDcsMTQ3IDQ5LDE0NiA1MiwxNDMgNTMsMTM5IDU0LDEzOCA1MywxMzIgNDksMTI4IDQyLDEyNSA0MCwxMjMgMzAsMTE4IFoiLz4KPHBhdGggZD0iTSA0MTcsODkgNDE0LDkwIDQxMiw5MiA0MDgsOTQgNDA1LDk3IDQwNCw5NyA0MDIsOTkgMzk1LDEwMyAzOTIsMTA2IDM5MSwxMDYgMzkzLDExMSAzOTQsMTExIDM5NywxMDggMzk4LDEwOCA0MDUsMTAzIDQxMSwxMTAgNDExLDExMSA0MDksMTEzIDQwOCwxMTMgNDA1LDExNiA0MDQsMTE2IDQwMCwxMTkgNDAwLDEyMCA0MDMsMTIzIDQwOCwxMTkgNDEyLDExNyA0MjcsMTA1IDQyOCwxMDUgNDI4LDEwMyA0MjYsMTAxIDQyNSwxMDEgNDIxLDEwNCA0MjAsMTA0IDQxNywxMDcgNDE1LDEwNyA0MDksMTAwIDQxOSw5MiA0MTksOTEgWiIvPgo8cGF0aCBkPSJNIDQ5LDg3IDQ2LDkxIDQ4LDkzIDUyLDk1IDU1LDk4IDU5LDEwMCA2MiwxMDMgNjAsMTA0IDU5LDEwMyA1NSwxMDMgNTQsMTAyIDUxLDEwMiA1MCwxMDEgNDcsMTAxIDQ2LDEwMCA0MCw5OSAzNywxMDMgMzcsMTA0IDQzLDEwOSA0NCwxMDkgNTAsMTE0IDUxLDExNCA1NCwxMTcgNTgsMTE5IDYxLDEyMiA2MywxMjIgNjUsMTIwIDY1LDExOCA1OCwxMTQgNTUsMTExIDU0LDExMSA0OSwxMDcgNTAsMTA2IDUyLDEwNiA1MywxMDcgNjEsMTA4IDYyLDEwOSA2NSwxMDkgNjYsMTEwIDcyLDExMSA3MiwxMTAgNzUsMTA2IFoiLz4KPHBhdGggZD0iTSA0MDIsNzEgMzk4LDY5IDM5MCw2OSAzODYsNzEgMzgwLDc2IDM3Niw4MyAzNzYsODkgMzc3LDkwIDM3OCw5NCAzODEsOTcgMzg1LDk5IDM4OCw5NiAzODksOTYgMzg3LDk1IDM4Miw5MCAzODIsODggMzgxLDg3IDM4Miw4NiAzODIsODMgMzg0LDgxIDM4NCw4MCAzODgsNzYgMzkyLDc0IDM5Nyw3NCAzOTksNzUgNDAyLDc4IDQwMyw4MSA0MDQsODEgNDA3LDc4IDQwNiw3NSBaIi8+CjxwYXRoIGQ9Ik0gNzEsNjMgNjYsNjggNjUsNzIgNjQsNzMgNjQsNzcgNjUsNzggNjUsODAgNjcsODQgNzMsOTAgNzQsOTAgNzgsOTMgODUsOTMgODYsOTIgODgsOTIgOTEsODkgOTIsODkgOTYsODQgOTYsODEgODUsNzAgODQsNzAgNzcsNzcgODAsODEgODEsODEgODQsNzggODUsNzggOTAsODMgODYsODcgODQsODggODEsODggODAsODcgNzYsODYgNzIsODIgNzAsNzggNzAsNzIgNzQsNjcgNzgsNjUgNzUsNjIgWiIvPgo8cGF0aCBkPSJNIDEwNiw1OCAxMDcsNTggMTExLDYyIDExMSw2NSAxMDcsNjkgMTAyLDYzIDEwMiw2MSBaIi8+CjxwYXRoIGQ9Ik0gOTksNDggMTAyLDUxIDEwMiw1NCAxMDAsNTcgOTgsNTcgOTQsNTIgOTQsNTEgOTYsNDkgOTgsNDkgWiIvPgo8cGF0aCBkPSJNIDM3Nyw0OCAzNzUsNDcgMzcxLDQ3IDM3MCw0OCAzNjgsNDggMzY0LDUyIDM2Myw1NCAzNjMsNjAgMzY1LDYzIDM2Niw2OCAzNjQsNzEgMzYwLDcxIDM1Niw2NyAzNTUsNjUgMzUyLDY5IDM1NCw3MyAzNTUsNzMgMzU5LDc2IDM2Myw3NyAzNjQsNzYgMzY2LDc2IDM3MCw3MiAzNzIsNjYgMzY5LDYwIDM2OSw1NSAzNzEsNTMgMzc1LDUzIDM3OSw1OCAzODIsNTUgMzgxLDUyIFoiLz4KPHBhdGggZD0iTSA5OCw0MyA5Nyw0NCA5NSw0NCA5Miw0NyA4OCw0OSA4Nyw1MSA5NSw2MSA5NSw2MiA5OCw2NSA5OCw2NiAxMDMsNzIgMTAzLDczIDEwNiw3NiAxMDgsNzQgMTEyLDcyIDExNSw2OSAxMTcsNjUgMTE3LDYyIDExNSw1OCAxMTMsNTYgMTExLDU1IDEwNyw1NSAxMDYsNTQgMTA3LDUzIDEwNyw1MSAxMDQsNDUgMTAzLDQ1IDEwMSw0MyBaIi8+CjxwYXRoIGQ9Ik0gMTI3LDMwIDEzMSwzMCAxMzcsMzYgMTM5LDQwIDEzOSw0OCAxMzQsNTIgMTMzLDUxIDEyOSw1MCAxMjMsNDIgMTIyLDM1IDEyMywzMyBaIi8+CjxwYXRoIGQ9Ik0gMTI1LDI1IDEyMSwyNyAxMTksMjkgMTE3LDMzIDExNyw0MSAxMjEsNDkgMTI1LDU0IDEyOSw1NiAxMzQsNTcgMTM1LDU2IDEzNyw1NiAxNDEsNTQgMTQzLDUyIDE0NCw0OCAxNDUsNDcgMTQ0LDM5IDE0MCwzMSAxMzYsMjcgMTMyLDI1IFoiLz4KPHBhdGggZD0iTSAzMjMsMTggMzE1LDM0IDMxNSwzNiAzMTAsNDYgMzE0LDQ4IDMyMCwzNyAzMjMsMzcgMzI2LDM5IDMyOCwzOSAzMjksNDAgMzI5LDQyIDMyNCw1MiAzMjUsNTQgMzI4LDU1IDMzMSw1MCAzMzEsNDggMzQyLDI2IDMzOCwyNCAzMzMsMzQgMzMyLDM1IDMzMCwzNSAzMjMsMzEgMzI4LDIxIDMyOCwyMCBaIi8+CjxwYXRoIGQ9Ik0gMTYyLDEwIDE2MSwxMSAxNTcsMTIgMTUzLDE2IDE1MiwyMCAxNTEsMjEgMTUxLDI2IDE1MiwyNyAxNTIsMzAgMTUzLDMxIDE1NCwzNSAxNTgsNDAgMTYyLDQyIDE3MSw0MiAxNzYsMzkgMTc1LDM1IDE3NCwzNCAxNzAsMzcgMTY0LDM3IDE1OCwzMSAxNTgsMjkgMTU3LDI4IDE1NywyMCAxNTgsMTggMTYxLDE1IDE2NywxNSAxNjcsMTEgMTY2LDEwIFoiLz4KPHBhdGggZD0iTSAyOTIsOSAyODUsMTUgMjgzLDE5IDI4MywyMSAyODIsMjIgMjgyLDI2IDI4MSwyNyAyODEsMjkgMjgyLDMwIDI4MiwzMyAyODMsMzUgMjg4LDQwIDMwMCw0MiAzMDEsNDAgMzAxLDM3IDMwMiwzNiAzMDIsMzMgMzAzLDMyIDMwMywyOSAzMDQsMjggMzA0LDI1IDMwMiwyNSAzMDEsMjQgMjk5LDI0IDI5NSwyMiAyOTQsMjMgMjk0LDI4IDI5NywyOCAyOTgsMjkgMjk3LDM1IDI5NSwzNyAyOTQsMzcgMjkzLDM2IDI5MSwzNiAyODgsMzMgMjg3LDMxIDI4NywyNCAyODgsMjMgMjg5LDE5IDI5MywxNSAyOTUsMTQgMzAwLDE0IDMwNiwxOCAzMDcsMTMgMzA1LDExIDMwMSwxMCAzMDAsOSBaIi8+CjxwYXRoIGQ9Ik0gMjcyLDMgMjY4LDMgMjY4LDcgMjY3LDggMjY3LDE0IDI2NiwxNSAyNjYsMjAgMjY1LDIxIDI2NSwyNiAyNjQsMjcgMjY0LDMyIDI2MywzNCAyNjcsMzQgMjY4LDM1IDI2OCwzMyAyNjksMzIgMjY5LDI3IDI3MCwyNiAyNzAsMjEgMjcxLDIwIDI3MSwxNSAyNzIsMTQgMjcyLDggMjczLDcgMjczLDQgWiIvPgo8cGF0aCBkPSJNIDIwMCwyIDE5NiwyIDE5Myw0IDE5Myw2IDE5MSw5IDE5MSwxMSAxODgsMTYgMTg2LDE1IDE4NSw2IDE4NCw1IDE4MSw1IDE4MCw2IDE4MCwxMCAxODEsMTEgMTgxLDE1IDE4MiwxNiAxODIsMjAgMTgzLDIxIDE4MywyNSAxODQsMjYgMTg0LDMwIDE4NSwzMSAxODUsMzYgMTg2LDM3IDE5MCwzNiAxOTAsMzEgMTg5LDMwIDE4OSwyNiAxODgsMjUgMTg5LDIzIDIwMCwzNSAyMDEsMzQgMjA0LDM0IDIwNiwzMyAxOTIsMTggWiIvPgo8cGF0aCBkPSJNIDIzMywwIDIzMywxMSAyMzIsMTIgMjMyLDMyIDIzNiwzMiAyMzYsMjggMjM3LDI3IDIzNywxOSAyMzgsMTggMjQ3LDE4IDI0OCwxOSAyNDgsMjIgMjQ3LDIzIDI0NywzMiAyNTIsMzIgMjUyLDE4IDI1MywxNyAyNTMsMSAyNDgsMSAyNDgsMTMgMjQ3LDE0IDI0NiwxMyAyMzgsMTMgMjM3LDEyIDIzOCwxMSAyMzgsMCBaIi8+CjwvZz4KPC9zdmc+"
LOGO_DATA_URI = f"data:image/svg+xml;base64,{LOGO_SVG_BASE64}"
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
    """비회원 방문증 이름을 이 기기(브라우저)의 쿠키에 저장합니다."""
    try:
        cookies["guest_pass_name"] = name
        cookies.save()
    except Exception:
        pass


def get_guest_pass_name() -> str:
    try:
        return cookies.get("guest_pass_name") or ""
    except Exception:
        return ""


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
.bk-pass-wrap {{
    max-width: 430px;
    margin: 0 auto 22px auto;
    padding: 4px;
}}
.bk-pass-card {{
    position: relative;
    overflow: hidden;
    border-radius: 24px;
    background: #F7F0DF;
    border: 1px solid #C99A4A;
    box-shadow: 0 18px 42px rgba(15,31,61,0.20), 0 3px 0 rgba(201,154,74,0.25);
    color: #14294A;
}}
.bk-pass-card::before {{
    content: "";
    position: absolute;
    inset: 9px;
    border: 1px solid rgba(201,154,74,0.65);
    border-radius: 17px;
    pointer-events: none;
    z-index: 10;
}}
.bk-pass-card::after {{
    content: "북악제  ·  2026";
    position: absolute;
    top: 16px;
    right: 24px;
    font-size: 9px;
    letter-spacing: 2px;
    font-weight: 800;
    color: rgba(20,41,74,0.45);
    z-index: 11;
}}
.bk-pass-top {{
    position: relative;
    padding: 36px 28px 30px;
    text-align: center;
    overflow: hidden;
    background:
        radial-gradient(circle at 15% 20%, rgba(201,154,74,0.18) 0 2px, transparent 3px),
        radial-gradient(circle at 85% 72%, rgba(201,154,74,0.16) 0 2px, transparent 3px),
        linear-gradient(145deg, #F7F0DF 0%, #EFE2C7 100%);
}}
.bk-pass-top::before {{
    content: "✦";
    position: absolute;
    left: 24px;
    top: 42px;
    color: #C99A4A;
    font-size: 22px;
    opacity: .9;
}}
.bk-pass-top::after {{
    content: "✦";
    position: absolute;
    right: 26px;
    bottom: 26px;
    color: #C99A4A;
    font-size: 18px;
    opacity: .9;
}}
.bk-pass-emblem {{
    width: 118px;
    height: 118px;
    object-fit: contain;
    margin: 10px auto 12px;
    display: block;
    position: relative;
    z-index: 2;
    filter: drop-shadow(0 3px 3px rgba(15,31,61,0.10));
}}
.bk-pass-kicker {{
    display: inline-block;
    padding: 5px 13px;
    border: 1px solid #C99A4A;
    border-radius: 999px;
    color: #7C5A24;
    background: rgba(255,255,255,0.18);
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 2.2px;
    margin-bottom: 9px;
    position: relative;
    z-index: 2;
}}
.bk-pass-title-main {{
    margin: 0;
    color: #0B63A7;
    font-family: 'Nanum Myeongjo', 'Noto Sans KR', serif;
    font-size: 45px;
    line-height: 1.05;
    font-weight: 900;
    letter-spacing: 10px;
    text-indent: 10px;
    position: relative;
    z-index: 2;
}}
.bk-pass-subtitle {{
    margin-top: 9px;
    color: #263B59;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.8px;
    position: relative;
    z-index: 2;
}}
.bk-pass-rule {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    margin-top: 17px;
    color: #C99A4A;
    position: relative;
    z-index: 2;
}}
.bk-pass-rule span:first-child, .bk-pass-rule span:last-child {{
    width: 72px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #C99A4A);
}}
.bk-pass-rule span:last-child {{
    background: linear-gradient(90deg, #C99A4A, transparent);
}}
.bk-pass-name-area {{
    margin: 20px 8px 0;
    padding: 13px 15px 12px;
    border: 1px solid rgba(11,99,167,0.22);
    border-radius: 12px;
    background: rgba(255,255,255,0.28);
    text-align: left;
    position: relative;
    z-index: 2;
}}
.bk-pass-name-label {{
    display: block;
    color: #7C5A24;
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 2px;
    margin-bottom: 5px;
}}
.bk-pass-name-box {{
    margin: 0;
    padding: 0;
    border: 0;
    font-size: 17px;
    font-weight: 900;
    color: #14294A;
}}
.bk-pass-name-box.empty {{
    color: #7F8792;
    font-weight: 600;
    font-size: 12px;
}}
.bk-pass-perforation {{
    height: 25px;
    position: relative;
    border-top: 2px dashed rgba(20,41,74,0.25);
    background: #F7F0DF;
}}
.bk-pass-perforation::before, .bk-pass-perforation::after {{
    content: "";
    position: absolute;
    top: -14px;
    width: 28px;
    height: 28px;
    background: {BG};
    border-radius: 50%;
    box-shadow: inset 0 0 0 1px rgba(201,154,74,0.22);
}}
.bk-pass-perforation::before {{ left: -14px; }}
.bk-pass-perforation::after {{ right: -14px; }}
.bk-pass-bottom {{
    position: relative;
    display: grid;
    grid-template-columns: 1fr 92px;
    gap: 0;
    min-height: 118px;
    background: #14294A;
    color: #F7F0DF;
}}
.bk-pass-bottom-left {{
    padding: 18px 18px 18px 24px;
    min-width: 0;
}}
.bk-pass-bl-title {{
    font-size: 18px;
    font-weight: 900;
    letter-spacing: 1px;
    color: #F7F0DF;
    margin-bottom: 10px;
}}
.bk-pass-meta-row {{
    font-size: 11px;
    color: rgba(247,240,223,0.82);
    margin-bottom: 5px;
}}
.bk-pass-vdivider {{
    position: absolute;
    right: 92px;
    top: 13px;
    bottom: 13px;
    border-left: 1px dashed rgba(247,240,223,0.45);
}}
.bk-pass-bottom-right {{
    padding: 15px 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    border-left: 1px dashed rgba(247,240,223,0.45);
}}
.bk-pass-date-label {{
    color: #D8B26A;
    font-size: 8px;
    font-weight: 900;
    letter-spacing: 1.5px;
    margin-bottom: 4px;
}}
.bk-pass-date-num {{
    color: #F7F0DF;
    font-size: 27px;
    line-height: 1;
    font-weight: 900;
}}
.bk-pass-date-num.month {{
    font-size: 11px;
    letter-spacing: 1px;
    margin-bottom: 4px;
    color: #D8B26A;
}}
.bk-pass-weekday-eng {{
    color: rgba(247,240,223,0.75);
    font-size: 8px;
    letter-spacing: 1.5px;
    margin-top: 5px;
}}
.bk-pass-footer {{
    padding: 8px 20px;
    text-align: center;
    background: #0B63A7;
    color: #F7F0DF;
    font-size: 8px;
    font-weight: 900;
    letter-spacing: 2px;
}}
@media (max-width: 520px) {{
    .bk-pass-wrap {{ max-width: 100%; }}
    .bk-pass-top {{ padding: 32px 20px 26px; }}
    .bk-pass-emblem {{ width: 102px; height: 102px; }}
    .bk-pass-title-main {{ font-size: 38px; letter-spacing: 7px; text-indent: 7px; }}
    .bk-pass-bottom {{ grid-template-columns: 1fr 78px; }}
    .bk-pass-vdivider {{ right: 78px; }}
    .bk-pass-bottom-right {{ padding-left: 6px; padding-right: 6px; }}
}}
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

    st.markdown('<div class="bk-section-title">주요 메뉴</div>', unsafe_allow_html=True)
    c1, c3 = st.columns(2)

    with c1:
        st.markdown(
            f"""
            <div class="bk-card">
                <h4>🎤 프로그램</h4>
                <div style="height:110px;border-radius:12px;margin-bottom:10px;
                            background:linear-gradient(135deg,{NAVY} 0%, {BLUE_PILL} 100%);
                            display:flex;align-items:center;justify-content:center;color:white;font-size:32px;">
                    🎤
                </div>
                <div style="color:{MUTED};font-size:13px;">
                    공연, 체험, 전시 등 북악제의 다양한 프로그램을 확인할 수 있습니다.
                </div>
                <a class="bk-card-btn" href="?nav={SLUG_BY_NAME['프로그램']}" target="_self">프로그램 보기 →</a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
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
                <h4>📅 시간표</h4>
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

    if is_member:
        visitor_name = user["name"]
    else:
        visitor_name = get_guest_pass_name()

    date_str = FESTIVAL_DATE.strftime("%Y. %m. %d")
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][FESTIVAL_DATE.weekday()]
    month_num = FESTIVAL_DATE.month
    day_num = FESTIVAL_DATE.day
    weekday_eng = FESTIVAL_DATE.strftime("%a").upper()

    if visitor_name:
        name_html = f'<div class="bk-pass-name-box">{visitor_name}{"  ·  회원" if is_member else "  ·  비회원"}</div>'
    else:
        name_html = '<div class="bk-pass-name-box empty">아래에서 이름을 등록하면 여기에 표시됩니다.</div>'

    st.markdown(
        f"""
        <div class="bk-pass-wrap">
            <div class="bk-pass-card">
                <div class="bk-pass-top">
                    <img src="{LOGO_DATA_URI}" class="bk-pass-emblem" alt="경복고등학교 로고">
                    <div class="bk-pass-kicker">KYUNGBOCK HIGH SCHOOL</div>
                    <div class="bk-pass-title-main">{FESTIVAL_NAME}</div>
                    <div class="bk-pass-subtitle">DIGITAL VISITOR PASS  ·  2026</div>
                    <div class="bk-pass-rule"><span></span><b>✦</b><span></span></div>
                    <div class="bk-pass-name-area">
                        <span class="bk-pass-name-label">VISITOR NAME</span>
                        {name_html}
                    </div>
                </div>
                <div class="bk-pass-perforation"></div>
                <div class="bk-pass-bottom">
                    <div class="bk-pass-bottom-left">
                        <div class="bk-pass-bl-title">경복고등학교 북악제</div>
                        <div class="bk-pass-meta-row">📍 경복고등학교 교내</div>
                        <div class="bk-pass-meta-row">📅 {date_str} ({weekday_kr})</div>
                        <div class="bk-pass-meta-row">✦ {FESTIVAL_SLOGAN}</div>
                    </div>
                    <div class="bk-pass-vdivider"></div>
                    <div class="bk-pass-bottom-right">
                        <div class="bk-pass-date-label">FESTIVAL DATE</div>
                        <div class="bk-pass-date-num month">{month_num:02d} / 30</div>
                        <div class="bk-pass-date-num">{day_num:02d}</div>
                        <div class="bk-pass-weekday-eng">{weekday_eng}</div>
                    </div>
                </div>
                <div class="bk-pass-footer">KYUNGBOCK HIGH SCHOOL  ·  BUKAKJE  ·  ADMIT ONE</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_member:
        st.caption("✅ 회원 정보로 로그인되어 있어 이름이 자동으로 표시됩니다.")
    else:
        st.markdown('<div class="bk-card">', unsafe_allow_html=True)
        st.write("**비회원 이름 등록**")
        st.markdown(
            f"<div style='color:{MUTED};font-size:13px;margin-bottom:10px;'>"
            "이름을 입력하고 저장하면, 이 기기(브라우저)에서는 다음에 다시 방문해도 "
            "같은 이름으로 방문증이 표시됩니다. 로그인 없이도 이용할 수 있어요.</div>",
            unsafe_allow_html=True,
        )
        with st.form("guest_pass_name_form", clear_on_submit=False):
            guest_input = st.text_input(
                "이름", value=visitor_name, placeholder="예: 홍길동", max_chars=20,
                label_visibility="collapsed",
            )
            submitted = st.form_submit_button("💾 이 이름으로 저장하기", use_container_width=True)
        if submitted:
            clean_name = guest_input.strip()
            if not clean_name:
                st.error("이름을 입력해주세요.")
            else:
                save_guest_pass_name(clean_name)
                st.success(f"'{clean_name}' 님의 이름으로 방문증에 저장했습니다.")
                st.rerun()

        if visitor_name:
            if st.button("🗑️ 저장된 이름 지우기", use_container_width=True):
                save_guest_pass_name("")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(
            f"<div style='color:{MUTED};font-size:12px;margin-top:8px;'>"
            "💡 회원으로 로그인하면 이름을 매번 입력할 필요 없이 자동으로 표시됩니다.</div>",
            unsafe_allow_html=True,
        )

    render_footer()


# ----------------------------------------------------------------------
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
        st.map(data={"lat": [37.5807], "lon": [126.9701]})
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
