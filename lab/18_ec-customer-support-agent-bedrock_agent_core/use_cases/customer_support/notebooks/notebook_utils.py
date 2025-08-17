"""
Jupyter 노트북을 위한 유틸리티 함수들
경로 설정 및 공통 import 기능 제공
"""

import sys
import os

def setup_project_path():
    """
    프로젝트 루트 경로를 Python path에 추가합니다.
    노트북에서 lab_helpers 모듈에 접근하기 위해 필요합니다.
    """
    # 현재 파일 위치에서 프로젝트 루트까지의 상대 경로
    # notebooks/ -> customer_support/ -> use_cases/ -> project_root/
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"📂 프로젝트 루트 경로 추가: {project_root}")
    
    return project_root

def import_lab_helpers():
    """
    lab_helpers 모듈을 안전하게 import합니다.
    """
    try:
        setup_project_path()
        from lab_helpers.utils import get_ssm_parameter, put_ssm_parameter
        from lab_helpers.ecommerce_memory import EcommerceCustomerMemoryHooks
        print("✅ lab_helpers 모듈 import 완료")
        return get_ssm_parameter, put_ssm_parameter, EcommerceCustomerMemoryHooks
    except ImportError as e:
        print(f"❌ lab_helpers import 실패: {e}")
        print("💡 대안: 노트북에서 다음 코드를 실행하세요:")
        print("""
import sys
import os
project_root = os.path.abspath(os.path.join(os.getcwd(), '../../..'))
sys.path.insert(0, project_root)
from lab_helpers.utils import get_ssm_parameter, put_ssm_parameter
        """)
        raise

def import_ecommerce_agent():
    """
    ecommerce_agent 모듈을 안전하게 import합니다.
    """
    try:
        setup_project_path()
        # 새로운 구조에서는 customer support agent를 import
        from use_cases.customer_support.agent import (
            SYSTEM_PROMPT,
            process_return, 
            process_exchange,
            web_search,
            MODEL_ID
        )
        print("✅ customer support agent 모듈 import 완료")
        return SYSTEM_PROMPT, process_return, process_exchange, web_search, MODEL_ID
    except ImportError:
        # 기존 파일에서 import 시도
        try:
            from legacy.original_files.ecommerce_agent import (
                SYSTEM_PROMPT,
                process_return, 
                process_exchange,
                web_search,
                MODEL_ID
            )
            print("✅ legacy ecommerce_agent 모듈 import 완료")
            return SYSTEM_PROMPT, process_return, process_exchange, web_search, MODEL_ID
        except ImportError as e:
            print(f"❌ ecommerce_agent import 실패: {e}")
            print("💡 노트북에서 해당 함수들을 직접 정의하거나 agent.py 파일을 확인하세요.")
            raise

if __name__ == "__main__":
    # 테스트
    print("🧪 notebook_utils 테스트")
    setup_project_path()
    print("✅ 경로 설정 완료")