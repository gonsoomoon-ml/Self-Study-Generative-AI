import math
import httpx
import json
import collections
import re
import pandas as pd
from dotenv import load_dotenv
import os
import sys

from mcp.server.fastmcp import FastMCP
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

# Initialize FastMCP server
mcp = FastMCP("kr-weather")

# 현재 초단기예보
ULTRA_API_URL = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst'
# 과거 단기 예보
PAST_OBS_API_URL = 'http://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList'

# API 키 설정
load_dotenv()
API_KR_WEATHER_SECRET = os.getenv('API_KR_WEATHER_SECRET')
if not API_KR_WEATHER_SECRET:
    raise RuntimeError('API_KR_WEATHER_SECRET 환경변수가 설정되어 있지 않습니다. .env 파일에 API_KR_WEATHER_SECRET=발급받은_키 를 추가하세요.')

# 주요 도시별 위도/경도/관측소ID 매핑
LOCATION_TABLE = {
    "서울":   {"latitude": 37.5665, "longitude": 126.9780, "stn_id": "108"},
    "부산":   {"latitude": 35.1796, "longitude": 129.0756, "stn_id": "159"},
    "대구":   {"latitude": 35.8722, "longitude": 128.6025, "stn_id": "143"},
    "인천":   {"latitude": 37.4563, "longitude": 126.7052, "stn_id": "112"},
    "광주":   {"latitude": 35.1595, "longitude": 126.8526, "stn_id": "156"},
    "대전":   {"latitude": 36.3504, "longitude": 127.3845, "stn_id": "133"},
    "울산":   {"latitude": 35.5384, "longitude": 129.3114, "stn_id": "152"},
    "세종":   {"latitude": 36.4801, "longitude": 127.2891, "stn_id": "239"},
    "수원":   {"latitude": 37.2636, "longitude": 127.0286, "stn_id": "119"},
    # 추가 주요 도시
    "창원":   {"latitude": 35.2285, "longitude": 128.6811, "stn_id": "155"},
    "전주":   {"latitude": 35.8242, "longitude": 127.1480, "stn_id": "146"},
    "청주":   {"latitude": 36.6424, "longitude": 127.4890, "stn_id": "131"},
    "포항":   {"latitude": 36.0190, "longitude": 129.3435, "stn_id": "138"},
    "제주":   {"latitude": 33.4996, "longitude": 126.5312, "stn_id": "184"},
    "강릉":   {"latitude": 37.7519, "longitude": 128.8761, "stn_id": "105"},
    "춘천":   {"latitude": 37.8813, "longitude": 127.7298, "stn_id": "101"},
    "평택":   {"latitude": 36.9946, "longitude": 127.0886, "stn_id": "203"},
    "안동":   {"latitude": 36.5684, "longitude": 128.7294, "stn_id": "136"},
    "여수":   {"latitude": 34.7604, "longitude": 127.6622, "stn_id": "168"},
    "목포":   {"latitude": 34.8118, "longitude": 126.3922, "stn_id": "165"},
    "진주":   {"latitude": 35.1802, "longitude": 128.1076, "stn_id": "192"},
    "원주":   {"latitude": 37.3422, "longitude": 127.9207, "stn_id": "114"},
    # 필요시 추가 도시...
}

def _mapToGrid(lat, lon) -> tuple[int, int]:
    '''
    위도/경도를 격자 좌표로 변환하는 함수
    Args:
        lat: 위도
        lon: 경도
    Returns:
        tuple[int, int]: 격자 좌표 (nx, ny)
    '''
    RE = 6371.00877     # 지도반경
    grid = 5.0          # 격자간격 (km)
    slat1 = 30.0        # 표준위도 1
    slat2 = 60.0        # 표준위도 2
    olon = 126.0        # 기준점 경도
    olat = 38.0         # 기준점 위도
    xo = 43             # 기준점 X좌표
    yo = 136            # 기준점 Y좌표
    PI = math.pi        # PI

    DEGRAD = PI / 180.0

    re = RE / grid
    slat1 = slat1 * DEGRAD
    slat2 = slat2 * DEGRAD
    olon = olon * DEGRAD
    olat = olat * DEGRAD

    sn = math.tan(PI * 0.25 + slat2 * 0.5) / math.tan(PI * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(PI * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(PI * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)    
    ra = math.tan(PI * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / pow(ra, sn)

    theta = lon * DEGRAD - olon

    if theta > PI:
        theta -= 2.0 * PI
    if theta < -PI:
        theta += 2.0 * PI

    theta *= sn

    nx = math.floor(ra * math.sin(theta) + xo + 0.5)
    ny = math.floor(ro - ra * math.cos(theta) + yo + 0.5)

    return (nx, ny)


async def _fetch_weather(lat: float, lon: float, api_url: str):
    SEOUL = ZoneInfo("Asia/Seoul")
    '''
    날씨 데이터를 요청하는 함수
    Args:
        lat: 위도
        lon: 경도
        api_url: 요청 URL
    Returns:
        dict: 날씨 데이터
    '''
    current_time = datetime.now(SEOUL)
    fcst_time = f"{current_time.hour:02d}00"
    current_time = current_time - timedelta(hours=1)
    base_time = f"{current_time.hour:02d}30"
    base_date = current_time.strftime('%Y%m%d')
    nx, ny = _mapToGrid(lat, lon)
    params ={
        'serviceKey' : API_KR_WEATHER_SECRET, 
        'pageNo' : 1, 
        'numOfRows' : '60', 
        'dataType' : 'JSON', 
        'base_date' : base_date, # 발표일자
        'base_time' : base_time, # 발표시각
        'nx' : nx, 
        'ny' : ny
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, params=params)
    if response.status_code != 200:
        print("API Error:", response.status_code, response.text, file=sys.stderr)
        return None
    try:
        result = response.json()
    except Exception as e:
        print("JSON 파싱 에러:", e, file=sys.stderr)
        print("응답 본문:", response.text, file=sys.stderr)
        return None
    # body 키가 있는지 확인
    if (
        'response' not in result or
        'body' not in result['response'] or
        'items' not in result['response']['body'] or
        'item' not in result['response']['body']['items']
    ):
        print("API 응답에 body/items/item이 없습니다. 전체 응답:", result, file=sys.stderr)
        return None
    items = result['response']['body']['items']['item']
    data = {}
    for item in items:
        if item['fcstTime'] == fcst_time:
            data[item['category']] = item['fcstValue']
    return data

# 기존 좌표 기반 함수는 내부용으로 변경
async def _get_now_forecast_by_coords(latitude: float, longitude: float) -> str:
    """
    Args:
        latitude: 위도
        longitude: 경도
    Returns:
        str: 실시간 초단기예보 정보
    """
    data = await _fetch_weather(latitude, longitude, ULTRA_API_URL)
    if not data:
        return "날씨 정보를 불러올 수 없습니다. (API 키 또는 네트워크 상태를 확인하세요)"
    sky = {'1': '맑음', '3': '구름많음', '4': '흐림'}.get(data.get('SKY', ''), '정보없음')
    pty = {
        '0': '없음', '1': '비', '2': '비나 눈', '3': '눈',
        '5': '빗방울', '6': '빗방울눈날림', '7': '눈날림'
    }.get(data.get('PTY', ''), '정보없음')
    rn1 = f"{data['RN1']}mm" if data.get('RN1', '0') not in ['0', '0.0', '', None] else '강수없음'
    forecast = f"""
기온: {data.get('T1H', '정보없음')}°C\n하늘상태: {sky}\n강수형태: {pty}\n습도: {data.get('REH', '정보없음')}%\n1시간 강수량: {rn1}\n"""
    return forecast

@mcp.tool()
async def get_now_forecast(location_name: str = "서울") -> str:
    """
    [MCP Tool] 실시간 초단기예보(실황/예보) 조회
    - 입력:
        - location_name (str): 조회할 도시명 (예: 서울, 수원, 부산 등)
    - 출력:
        - 현재 시각 기준의 기온, 하늘상태, 강수형태, 습도, 1시간 강수량 등 실황 정보를 텍스트로 반환
    - 제한:
        - 지원하지 않는 도시명 입력 시 안내 메시지 반환
        - 대한민국 기상청 초단기예보 API 기준, 한반도 내 주요 도시만 지원
        - 네트워크/API 오류 시 안내 메시지 반환
    - 예시:
        get_now_forecast(location_name="서울")
        # → "기온: 24°C\n하늘상태: 흐림\n강수형태: 없음\n습도: 40%\n1시간 강수량: 강수없음"
    """
    info = LOCATION_TABLE.get(location_name)
    if not info:
        return f"지원하지 않는 도시명입니다: {location_name}"
    latitude = info["latitude"]
    longitude = info["longitude"]
    return await _get_now_forecast_by_coords(latitude, longitude)

@mcp.tool()
async def get_past_weather_stats(
    location_name: str = "서울",
    start_dt: str = None,
    end_dt: str = None,
    start_hh: str = '01',
    end_hh: str = '23'
) -> str:
    """
    [MCP Tool] 도시별 과거 날씨 통계(일별 최고/최저기온, 평균 강수량 등) 조회
    - 입력: 
        - location_name: 도시명 (예: 서울, 부산, 수원 등)
        - start_dt: 조회 시작일 (YYYYMMDD)
        - end_dt: 조회 종료일 (YYYYMMDD)
        - (선택) start_hh, end_hh: 시간 단위 조회 시 시작/끝 시각 (기본 01~23)
    - 출력: 
        - 일별 최고/최저기온, 평균 강수량, 온도/강수 설명 (JSON)
        - location: 지역명, 위도, 경도 정보
    - 제한: 
        - 최대 2주(14일) 이내만 조회 가능 (초과 시 안내 메시지 반환)
    - 예시:
        get_past_weather_stats(location_name="서울", start_dt="20250501", end_dt="20250514")
    """
    from datetime import datetime, timedelta
    # 도시 정보 lookup
    info = LOCATION_TABLE.get(location_name)
    if not info:
        return json.dumps({"error": f"지원하지 않는 도시명입니다: {location_name}"}, ensure_ascii=False)
    stn_id = info["stn_id"]
    latitude = info["latitude"]
    longitude = info["longitude"]
    # 날짜 기본값: 1주일 전~어제
    if not end_dt or not start_dt:
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=6)
        start_dt = start_date.strftime('%Y%m%d')
        end_dt = end_date.strftime('%Y%m%d')
    # 날짜 차이 계산 (YYYYMMDD)
    start_date = datetime.strptime(start_dt, '%Y%m%d')
    end_date = datetime.strptime(end_dt, '%Y%m%d')
    delta_days = (end_date - start_date).days + 1
    if delta_days > 14:
        new_end_date = start_date + timedelta(days=13)
        guide = f"요청하신 기간({delta_days}일)은 2주(14일)까지 가능합니다. 2주 이내로 입력해 주세요."
        # 2주 초과 시 안내 메시지만 반환
        location_info = {
            "name": location_name,
            "latitude": latitude,
            "longitude": longitude
        }
        return json.dumps({"guide": guide, "location": location_info}, ensure_ascii=False, indent=2)
    else:
        guide = None
    # 시간 단위 데이터 요청 (직접 API 호출)
    params = {
        'ServiceKey': API_KR_WEATHER_SECRET,
        'pageNo': '1',
        'numOfRows': '500',
        'dataType': 'JSON',
        'dataCd': 'ASOS',
        'dateCd': 'HR',
        'startDt': start_dt,
        'endDt': end_dt,
        'stnIds': stn_id,
        'startHh': start_hh or '01',
        'endHh': end_hh or '23'
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(PAST_OBS_API_URL, params=params)
    if response.status_code != 200:
        return f"API Error: {response.status_code} {response.text}"
    try:
        data = response.json()
    except Exception as e:
        return f"JSON 파싱 에러: {e}\n응답 본문: {response.text}"
    
    if (
        'response' not in data or
        'body' not in data['response'] or
        'items' not in data['response']['body'] or
        'item' not in data['response']['body']['items']
    ):
        return f"API 응답에 body/items/item이 없습니다. 전체 응답: {json.dumps(data, ensure_ascii=False)}"
    
    items = data['response']['body']['items']['item']
    # 표 형태 문자열 생성 (기존 raw와 동일하게)
    result_lines = ["일시      기온(°C)  강수량(mm)"]
    for item in items:
        tm = item.get('tm', '-')
        ta = item.get('ta', '-')
        rn = item.get('rn', '-')
        result_lines.append(f"{tm}  {ta}      {rn}")
    raw = '\n'.join(result_lines)
    # 파싱: 표 형태 문자열을 라인별로 분리
    lines = raw.splitlines()
    if len(lines) < 2:
        return json.dumps({"error": "데이터 없음", "raw": raw}, ensure_ascii=False)
    header = lines[0].split()
    data_lines = lines[1:]
    records = []
    for line in data_lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        tm = f"{parts[0]} {parts[1]}"
        try:
            ta = float(parts[2])
        except Exception as e:
            print(f"[WARN] 온도 변환 오류: {parts[2]}, 에러: {e}", file=sys.stderr)
            ta = None
        if len(parts) > 3:
            try:
                rn = float(parts[3])
            except Exception as e:
                print(f"[WARN] 강수량 변환 오류: {parts[3]}, 에러: {e}", file=sys.stderr)
                rn = 0.0
        else:
            rn = 0.0
        records.append({"tm": tm, "ta": ta, "rn": rn})
    if not records:
        return json.dumps({"error": "데이터 없음", "raw": raw}, ensure_ascii=False)
    import pandas as pd
    df = pd.DataFrame(records)
    df['date'] = df['tm'].str[:10]
    df['ta'] = pd.to_numeric(df['ta'], errors='coerce').fillna(0)
    df['rn'] = pd.to_numeric(df['rn'], errors='coerce').fillna(0)
    result = (
        df.groupby('date').agg(
            max_temp=('ta', 'max'),
            min_temp=('ta', 'min'),
            avg_rain=('rn', 'mean')
        ).round(2)
        .reset_index().set_index('date')
    )
    def temp_desc(row):
        max_t = row['max_temp']
        if max_t < 10:
            return '춥다'
        elif max_t < 20:
            return '선선하다'
        elif max_t < 28:
            return '덥다'
        else:
            return '매우 덥다'
    def rain_desc(row):
        rain = row['avg_rain']
        if rain == 0:
            return '강수 없음'
        elif rain < 5:
            return '강수 적음'
        else:
            return '강수 많음'
    result['temp_desc'] = result.apply(temp_desc, axis=1)
    result['rain_desc'] = result.apply(rain_desc, axis=1)
    result = result.to_dict(orient='index')
    # 날짜 구간 전체 생성
    all_dates = []
    cur = start_date
    while cur <= end_date:
        all_dates.append(cur.strftime('%Y-%m-%d'))
        cur += timedelta(days=1)
    # 누락된 날짜는 '데이터 없음'으로 추가
    for d in all_dates:
        if d not in result:
            result[d] = {"error": "데이터 없음"}
    # (정렬 보장)
    result = {d: result[d] for d in sorted(result)}
    # location 정보 추가
    location_info = {
        "name": location_name,
        "latitude": latitude,
        "longitude": longitude
    }
    if guide:
        return json.dumps({"guide": guide, "location": location_info, "data": result}, ensure_ascii=False, indent=2)
    else:
        return json.dumps({"location": location_info, "data": result}, ensure_ascii=False, indent=2)

def run_tests():
    import asyncio
    import sys
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    # 지역 정보 변수화
    location_name = "서울"  # 원하는 도시명만 지정
    # 테스트용 시작일, 종료일 변수
    start_dt = "20250528"  # 원하는 시작일(YYYYMMDD)
    end_dt = "20250603"    # 원하는 종료일(YYYYMMDD)
    # 현재 시간 (서울 기준)
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[현재 시간] {now}")
    print(f"[지역 정보] {location_name}")
    print("[get_now_forecast] (초단기예보)")
    result_now = asyncio.run(get_now_forecast(location_name))
    print(result_now)
    # 사용자 입력: 시작일, 종료일
    if len(sys.argv) == 3:
        start_dt = sys.argv[1]
        end_dt = sys.argv[2]
    # else: start_dt, end_dt는 위에서 지정한 변수값 사용
    print(f"\n[get_past_weather_stats] ({start_dt}~{end_dt}, 일별 평균)")
    print(f"[현재 시간] {now}")
    print(f"[지역 정보] {location_name}")
    result_daily_stats = asyncio.run(get_past_weather_stats(
        location_name=location_name,
        start_dt=start_dt,
        end_dt=end_dt,
        start_hh='01',
        end_hh='23'
    ))
    print(result_daily_stats)

if __name__ == "__main__":
    import sys
    import warnings
    import os

    # 모든 경고를 stderr로 출력
    def warn_with_traceback(message, category, filename, lineno, file=None, line=None):
        print(f"{filename}:{lineno}: {category.__name__}: {message}", file=sys.stderr)
    warnings.showwarning = warn_with_traceback

    # 예외 발생 시 traceback을 stderr로만 출력
    def excepthook(type, value, traceback):
        import traceback as tb
        tb.print_exception(type, value, traceback, file=sys.stderr)
    sys.excepthook = excepthook

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 테스트 모드: run_tests()만 실행
        run_tests()
    else:
        # MCP 서버 모드: stdout 완전 차단
        sys.stdout = open(os.devnull, "w")
        mcp.run(transport='stdio')

    
