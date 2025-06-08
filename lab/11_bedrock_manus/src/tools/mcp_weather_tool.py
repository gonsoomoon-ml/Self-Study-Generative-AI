"""
MCP Weather Tool for collecting Korean historical weather data
"""
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def validate_date_format(date_str: str) -> bool:
    """Validate date format YYYYMMDD"""
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return True
    except ValueError:
        return False

def validate_date_range(start_dt: str, end_dt: str) -> tuple[bool, str]:
    """Validate date range (max 14 days, no future dates)"""
    try:
        start_date = datetime.strptime(start_dt, "%Y%m%d")
        end_date = datetime.strptime(end_dt, "%Y%m%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        
        # Check if dates are in the future
        if start_date >= today or end_date >= today:
            return False, "날짜는 어제 이전만 가능합니다. 오늘이나 미래 날짜는 조회할 수 없습니다."
        
        # Check if date range exceeds 14 days
        if (end_date - start_date).days > 13:  # 14 days = 0-13 range
            return False, "조회 기간은 최대 14일까지만 가능합니다."
        
        # Check if start_date is after end_date
        if start_date > end_date:
            return False, "시작일이 종료일보다 늦을 수 없습니다."
            
        return True, "Valid date range"
    except ValueError:
        return False, "잘못된 날짜 형식입니다. YYYYMMDD 형식을 사용해주세요."

async def collect_weather_data_via_mcp(
    location_name: str = None,
    start_dt: str = None,
    end_dt: str = None,
    start_hh: str = None,
    end_hh: str = None
) -> Dict[str, Any]:
    """
    MCP를 통해 날씨 데이터를 수집합니다.
    
    Args:
        location_name: 한국 도시명 (예: 서울, 부산, 대구)
        start_dt: 시작일 (YYYYMMDD)
        end_dt: 종료일 (YYYYMMDD)
        start_hh: 시작 시간 (01-23)
        end_hh: 종료 시간 (01-23)
    
    Returns:
        Dict containing weather data and file path
    """
    try:
        # Import MCP client
        from langchain_mcp_adapters.client import MultiServerMCPClient
        
        # 환경변수에서 기본값 설정
        location_name = location_name or os.getenv("DEFAULT_LOCATION", "서울")
        start_hh = start_hh or os.getenv("DEFAULT_TIME_RANGE_START", "01")
        end_hh = end_hh or os.getenv("DEFAULT_TIME_RANGE_END", "23")
        
        # MCP 서버 설정 (환경변수에서 읽기)
        SERVER_URL = os.getenv("MCP_SERVER_URL", "http://34.212.60.123:8000/mcp/")
        MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable_http")
        
        print(f"🔗 MCP 서버 URL: {SERVER_URL}")
        print(f"🏙️ 조회 도시: {location_name}")
        print(f"⏰ 시간 범위: {start_hh}:00 ~ {end_hh}:00")
        
        client = MultiServerMCPClient(
            {
                "kr-weather": {
                    "url": SERVER_URL,
                    "transport": MCP_TRANSPORT,
                }
            }
        )
        
        # 날짜 유효성 검사
        if not start_dt or not end_dt:
            return {
                "success": False,
                "error": "시작일과 종료일은 필수입니다.",
                "file_path": None
            }
        
        if not validate_date_format(start_dt) or not validate_date_format(end_dt):
            return {
                "success": False,
                "error": "날짜 형식이 올바르지 않습니다. YYYYMMDD 형식을 사용해주세요.",
                "file_path": None
            }
        
        is_valid, error_msg = validate_date_range(start_dt, end_dt)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg,
                "file_path": None
            }
        
        print(f"🌤️ MCP 날씨 데이터 수집 시작: {location_name} ({start_dt} ~ {end_dt})")
        
        # MCP 도구 가져오기
        tools = await client.get_tools()
        print(f"✅ MCP 도구 연결 성공: {len(tools)}개 도구 사용 가능")
        
        # get_past_weather_stats 도구 찾기
        weather_tool = None
        for tool in tools:
            if hasattr(tool, 'name') and 'weather' in tool.name.lower():
                weather_tool = tool
                break
        
        if not weather_tool:
            # 첫 번째 도구를 weather 도구로 가정
            weather_tool = tools[0] if tools else None
        
        if not weather_tool:
            return {
                "success": False,
                "error": "MCP 서버에서 날씨 도구를 찾을 수 없습니다.",
                "file_path": None
            }
        
        # 날씨 데이터 수집
        print(f"📡 날씨 데이터 요청 중...")
        params = {
            "location_name": location_name,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "start_hh": start_hh,
            "end_hh": end_hh
        }
        result = await weather_tool.ainvoke(params)
        
        print("✅ 날씨 데이터 수집 완료!")
        
        # 결과 파일 저장 (JSON과 메타데이터 분리)
        os.makedirs('./artifacts', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. 순수 JSON 파일 저장
        json_filename = f'./artifacts/weather_data_{timestamp}.json'
        
        # MCP 서버 결과를 JSON 객체로 파싱
        if isinstance(result, str):
            # 문자열인 경우 JSON으로 파싱 시도
            try:
                weather_json = json.loads(result)
            except json.JSONDecodeError:
                # JSON이 아닌 경우 문자열 그대로 저장
                weather_json = {"raw_data": result}
        else:
            # 이미 딕셔너리인 경우
            weather_json = result
        
        # 메타데이터를 JSON에 추가
        enhanced_weather_data = {
            "metadata": {
                "city": location_name,
                "period_start": start_dt,
                "period_end": end_dt,
                "time_range": f"{start_hh}:00-{end_hh}:00",
                "collected_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "data_size_chars": len(str(result))
            },
            "weather_data": weather_json
        }
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(enhanced_weather_data, f, ensure_ascii=False, indent=2)
        
        # 2. 간단한 메타데이터 텍스트 파일도 저장 (호환성용)
        meta_filename = f'./artifacts/weather_meta_{timestamp}.txt'
        with open(meta_filename, 'w', encoding='utf-8') as f:
            f.write(f"MCP 날씨 데이터 수집 결과\n")
            f.write(f"도시: {location_name}\n")
            f.write(f"기간: {start_dt} ~ {end_dt}\n")
            f.write(f"시간: {start_hh}:00 ~ {end_hh}:00\n")
            f.write(f"수집 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"데이터 크기: {len(str(result))} 문자\n")
            f.write(f"JSON 파일: {json_filename}\n")
        
        print(f"💾 JSON 파일 저장 완료: {json_filename}")
        print(f"📋 메타데이터 파일 저장 완료: {meta_filename}")
        
        return {
            "success": True,
            "data": result,
            "file_path": json_filename,  # JSON 파일 경로 반환
            "meta_file_path": meta_filename,  # 메타데이터 파일 경로 추가
            "location": location_name,
            "period": f"{start_dt} ~ {end_dt}",
            "timestamp": timestamp
        }
        
    except ImportError as e:
        return {
            "success": False,
            "error": f"MCP 클라이언트 라이브러리를 찾을 수 없습니다: {str(e)}",
            "file_path": None
        }
    except ConnectionError as e:
        return {
            "success": False,
            "error": f"MCP 서버 연결 실패: {str(e)}",
            "file_path": None
        }
    except Exception as e:
        error_msg = f"MCP 날씨 데이터 수집 중 오류 발생: {str(e)}"
        print(f"❌ {error_msg}")
        
        # 오류도 파일로 저장
        os.makedirs('./artifacts', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_filename = f'./artifacts/weather_error_{timestamp}.txt'
        
        with open(error_filename, 'w', encoding='utf-8') as f:
            f.write(f"# MCP 날씨 데이터 수집 오류\n")
            f.write(f"# 요청 도시: {location_name}\n")
            f.write(f"# 요청 기간: {start_dt} ~ {end_dt}\n")
            f.write(f"# 오류 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 오류 내용: {error_msg}\n")
        
        return {
            "success": False,
            "error": error_msg,
            "file_path": error_filename
        }

def handle_mcp_weather_tool(**kwargs) -> str:
    """
    동기 함수에서 비동기 MCP weather tool을 호출하는 핸들러
    """
    try:
        # 환경변수에서 기본값 설정
        default_location = os.getenv("DEFAULT_LOCATION", "서울")
        default_start_hh = os.getenv("DEFAULT_TIME_RANGE_START", "01")
        default_end_hh = os.getenv("DEFAULT_TIME_RANGE_END", "23")
        
        location_name = kwargs.get('location_name', default_location)
        start_dt = kwargs.get('start_dt')
        end_dt = kwargs.get('end_dt')
        start_hh = kwargs.get('start_hh', default_start_hh)
        end_hh = kwargs.get('end_hh', default_end_hh)
        
        # 비동기 함수 실행
        result = asyncio.run(collect_weather_data_via_mcp(
            location_name=location_name,
            start_dt=start_dt,
            end_dt=end_dt,
            start_hh=start_hh,
            end_hh=end_hh
        ))
        
        if result["success"]:
            response = f"""
🌤️ MCP 날씨 데이터 수집 완료!

📍 수집 정보:
- 도시: {result['location']}
- 기간: {result['period']}
- 파일: {result['file_path']}

✅ 날씨 데이터가 성공적으로 수집되어 파일로 저장되었습니다.
Reporter 에이전트가 이 파일을 사용하여 최종 보고서를 작성할 수 있습니다.

📁 생성된 파일: {result['file_path']}
"""
        else:
            response = f"""
❌ MCP 날씨 데이터 수집 실패

오류 내용: {result['error']}

💡 해결 방안:
1. 날짜 형식이 YYYYMMDD인지 확인
2. 조회 기간이 14일 이내인지 확인  
3. 오늘이나 미래 날짜가 포함되지 않았는지 확인
4. MCP 서버 연결 상태 확인

"""
            if result.get('file_path'):
                response += f"📁 오류 로그 파일: {result['file_path']}"
        
        return response
        
    except Exception as e:
        return f"❌ MCP weather tool 실행 중 치명적 오류: {str(e)}" 