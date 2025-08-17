"""
웹 검색 및 스타일링 도구들
"""

from strands.tools import tool
from typing import Dict, Any, List
import json


@tool
def web_search(query: str, search_type: str = "styling") -> Dict[str, Any]:
    """
    웹에서 스타일링 정보나 트렌드를 검색합니다.
    
    Args:
        query: 검색 쿼리
        search_type: 검색 유형 (styling/trend/product)
        
    Returns:
        검색 결과
    """
    
    # 모의 검색 결과 (실제로는 DuckDuckGo 또는 다른 검색 API 사용)
    mock_results = {
        "styling": {
            "query": query,
            "results": [
                {
                    "title": f"{query} 스타일링 가이드",
                    "snippet": f"{query}를 활용한 최신 코디법과 스타일링 팁을 소개합니다.",
                    "url": "https://fashion.naver.com/styling-guide",
                    "relevance_score": 0.95
                },
                {
                    "title": f"{query} 2024 트렌드",
                    "snippet": f"올해 가장 인기 있는 {query} 스타일과 컬러 조합을 확인해보세요.",
                    "url": "https://www.elle.co.kr/fashion-trend",
                    "relevance_score": 0.88
                }
            ],
            "suggestions": [
                f"{query} 겨울 코디",
                f"{query} 데일리룩",
                f"{query} 컬러 매칭"
            ]
        },
        "trend": {
            "query": query,
            "results": [
                {
                    "title": f"2024 {query} 트렌드 전망",
                    "snippet": f"패션 업계 전문가들이 예측하는 {query} 트렌드 분석입니다.",
                    "url": "https://www.vogue.co.kr/fashion/trend",
                    "relevance_score": 0.92
                }
            ]
        }
    }
    
    return mock_results.get(search_type, mock_results["styling"])


@tool
def get_styling_recommendations(
    item_type: str,
    season: str = "current",
    occasion: str = "casual"
) -> Dict[str, Any]:
    """
    특정 아이템에 대한 스타일링 추천을 제공합니다.
    
    Args:
        item_type: 아이템 종류 (top, bottom, dress, etc.)
        season: 계절 (spring, summer, fall, winter, current)
        occasion: 상황 (casual, formal, date, work)
        
    Returns:
        스타일링 추천
    """
    
    # 계절별, 상황별 스타일링 데이터베이스
    styling_db = {
        "top": {
            "casual": {
                "combinations": [
                    {"bottom": "jeans", "shoes": "sneakers", "description": "편안한 데일리룩"},
                    {"bottom": "wide_pants", "shoes": "loafers", "description": "트렌디한 캐주얼"}
                ],
                "colors": ["white", "beige", "navy", "gray"],
                "accessories": ["minimal_earrings", "crossbody_bag"]
            },
            "formal": {
                "combinations": [
                    {"bottom": "slacks", "shoes": "heels", "description": "오피스룩"},
                    {"bottom": "pencil_skirt", "shoes": "pumps", "description": "비즈니스 미팅"}
                ],
                "colors": ["black", "navy", "white", "beige"],
                "accessories": ["watch", "structured_bag"]
            }
        },
        "dress": {
            "casual": {
                "combinations": [
                    {"outer": "denim_jacket", "shoes": "sneakers", "description": "캐주얼 원피스룩"},
                    {"outer": "cardigan", "shoes": "flats", "description": "페미닌 스타일"}
                ]
            },
            "formal": {
                "combinations": [
                    {"outer": "blazer", "shoes": "heels", "description": "세미 포멀"},
                    {"outer": "coat", "shoes": "pumps", "description": "포멀 이벤트"}
                ]
            }
        }
    }
    
    recommendations = styling_db.get(item_type, {}).get(occasion, {})
    
    return {
        "item_type": item_type,
        "season": season,
        "occasion": occasion,
        "recommendations": recommendations,
        "tips": {
            "ko": [
                "체형에 맞는 핏을 선택하세요.",
                "컬러 조합을 고려해보세요.",
                "액세서리로 포인트를 주세요.",
                "상황에 맞는 신발을 선택하세요."
            ]
        }
    }


@tool
def get_color_matching_advice(primary_color: str, item_type: str) -> Dict[str, Any]:
    """
    색상 매칭 조언을 제공합니다.
    
    Args:
        primary_color: 기본 색상
        item_type: 아이템 종류
        
    Returns:
        색상 매칭 조언
    """
    
    color_combinations = {
        "black": {
            "complements": ["white", "gray", "red", "gold"],
            "avoid": [],
            "tips": "블랙은 모든 색상과 잘 어울리는 만능 컬러입니다."
        },
        "white": {
            "complements": ["black", "navy", "beige", "pastel"],
            "avoid": ["cream"],
            "tips": "화이트는 깔끔하고 세련된 느낌을 줍니다."
        },
        "navy": {
            "complements": ["white", "beige", "red", "yellow"],
            "avoid": ["black"],
            "tips": "네이비는 블랙보다 부드러운 느낌의 베이직 컬러입니다."
        },
        "beige": {
            "complements": ["white", "brown", "navy", "green"],
            "avoid": [],
            "tips": "베이지는 자연스럽고 따뜻한 느낌을 줍니다."
        }
    }
    
    advice = color_combinations.get(primary_color, {
        "complements": ["neutral tones"],
        "avoid": [],
        "tips": "색상 조합에 대한 개인적인 취향을 고려해보세요."
    })
    
    return {
        "primary_color": primary_color,
        "item_type": item_type,
        "matching_colors": advice["complements"],
        "colors_to_avoid": advice["avoid"],
        "styling_tip": advice["tips"],
        "seasonal_recommendations": {
            "spring": ["pastel", "light"],
            "summer": ["bright", "vivid"],
            "fall": ["warm", "earth_tone"],
            "winter": ["deep", "dark"]
        }
    }