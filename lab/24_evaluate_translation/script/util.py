"""
Common utilities for translation evaluation
"""

import sys

from huggingface_hub import HfFolder


def check_hf_login():
    """Check if user is logged in to HuggingFace Hub."""
    token = HfFolder.get_token()
    if token is None:
        print("ERROR: HuggingFace login required.")
        print()
        print("Please run:")
        print("  huggingface-cli login")
        print()
        print("Or set token:")
        print("  huggingface-cli login --token YOUR_TOKEN")
        sys.exit(1)
    print("HuggingFace login: OK")


def get_sample_data() -> list[dict]:
    """Return sample translation data (Korean -> English)."""
    return [
        # Short examples
        {
            "src": "오늘 날씨가 정말 좋습니다.",
            "mt": "The weather is really nice today."
        },
        {
            "src": "안녕하세요, 오늘 기분이 어떠세요?",
            "mt": "Hello, how are you feeling today?"
        },
        {
            "src": "이 프로젝트는 기계 번역 품질을 평가합니다.",
            "mt": "This project evaluates machine translation quality."
        },
        # Longer examples (~500 tokens)
        {
            "src": "에이전틱 AI는 인공지능의 새로운 패러다임으로, 단순히 질문에 답하는 것을 넘어 스스로 목표를 설정하고 계획을 세우며 행동을 실행하는 자율적인 시스템을 말합니다. 기존의 챗봇이나 언어 모델이 사용자의 명령에 수동적으로 반응했다면, 에이전틱 AI는 주어진 목표를 달성하기 위해 여러 단계의 작업을 스스로 분해하고 실행합니다. 예를 들어 여행 계획을 요청하면 항공편 검색, 호텔 예약, 일정 최적화까지 모든 과정을 자동으로 처리할 수 있습니다. 이러한 시스템의 핵심은 도구 사용 능력입니다. 에이전트는 웹 검색, 코드 실행, API 호출, 파일 관리 등 다양한 도구를 상황에 맞게 선택하고 활용합니다. 또한 작업 중 오류가 발생하면 스스로 문제를 진단하고 대안을 찾아 다시 시도합니다. 최근에는 여러 에이전트가 협력하는 멀티 에이전트 시스템도 등장했습니다. 연구원 에이전트가 정보를 수집하고, 분석가 에이전트가 데이터를 처리하며, 작성자 에이전트가 보고서를 만드는 식으로 역할을 분담합니다. 기업들은 고객 서비스, 소프트웨어 개발, 데이터 분석 등 다양한 분야에서 에이전틱 AI를 도입하고 있으며, 이는 업무 자동화의 새로운 장을 열고 있습니다. 물론 자율성이 높아질수록 안전성과 제어 가능성에 대한 논의도 중요해지고 있습니다.",
            "mt": "Agentic AI represents a new paradigm in artificial intelligence, referring to autonomous systems that go beyond simply answering questions to setting their own goals, making plans, and executing actions. While traditional chatbots and language models passively responded to user commands, agentic AI independently breaks down and executes multi-step tasks to achieve given objectives. For example, when asked to plan a trip, it can automatically handle the entire process from searching flights, booking hotels, to optimizing schedules. The core of such systems is their ability to use tools. Agents select and utilize various tools such as web search, code execution, API calls, and file management according to the situation. Additionally, when errors occur during tasks, they diagnose problems themselves and try again by finding alternatives. Recently, multi-agent systems where multiple agents collaborate have also emerged. Research agents collect information, analyst agents process data, and writer agents create reports, dividing roles accordingly. Companies are adopting agentic AI in various fields including customer service, software development, and data analysis, opening a new chapter in work automation. Of course, as autonomy increases, discussions about safety and controllability are becoming increasingly important."
        },
        {
            "src": "한국의 전통 음식 문화는 수천 년의 역사를 가지고 있으며, 계절과 지역에 따라 다양한 재료와 조리법이 발달해 왔습니다. 김치, 불고기, 비빔밥 같은 대표적인 한국 음식들은 이제 전 세계적으로 사랑받고 있으며, 한식의 건강한 발효 식품과 균형 잡힌 영양 구성은 현대인들에게 큰 관심을 받고 있습니다. 특히 김치는 유네스코 인류무형문화유산으로 등재될 만큼 그 가치를 인정받고 있습니다. 김치에는 유산균이 풍부하게 들어있어 장 건강에 도움이 되며, 비타민과 식이섬유도 많이 함유하고 있습니다. 한국인들은 계절마다 다른 김치를 담그는데, 봄에는 파김치, 여름에는 오이소박이, 가을에는 배추김치, 겨울에는 동치미를 주로 먹습니다. 불고기는 달콤한 간장 양념에 재운 소고기를 구워 먹는 요리로, 부드러운 식감과 깊은 맛으로 외국인들에게도 인기가 높습니다. 비빔밥은 밥 위에 다양한 나물과 고기, 계란을 올리고 고추장을 넣어 비벼 먹는 음식으로, 영양적으로 균형 잡힌 한 끼 식사가 됩니다. 최근에는 한류의 영향으로 한식에 대한 관심이 더욱 높아지고 있으며, 세계 각국에서 한식당을 쉽게 찾아볼 수 있게 되었습니다. 한국 정부도 한식의 세계화를 위해 다양한 정책을 추진하고 있으며, 한식 요리사 양성 프로그램과 해외 한식당 지원 사업 등을 진행하고 있습니다.",
            "mt": "Korean traditional food culture has a history of thousands of years, and various ingredients and cooking methods have developed according to seasons and regions. Representative Korean dishes such as kimchi, bulgogi, and bibimbap are now loved worldwide, and the healthy fermented foods and balanced nutritional composition of Korean cuisine are attracting great interest from modern people. In particular, kimchi has been recognized for its value to the extent that it was inscribed on the UNESCO Intangible Cultural Heritage list. Kimchi is rich in lactic acid bacteria that help intestinal health and contains many vitamins and dietary fiber. Koreans make different types of kimchi each season: green onion kimchi in spring, cucumber kimchi in summer, cabbage kimchi in autumn, and radish water kimchi in winter. Bulgogi is a dish of grilled beef marinated in sweet soy sauce, popular among foreigners for its tender texture and deep flavor. Bibimbap is a dish where various vegetables, meat, and eggs are placed on rice and mixed with red pepper paste, making it a nutritionally balanced meal. Recently, interest in Korean food has increased even more due to the influence of Hallyu, and Korean restaurants can now be easily found in countries around the world. The Korean government is also promoting various policies for the globalization of Korean food, including training programs for Korean cuisine chefs and support projects for overseas Korean restaurants."
        },
    ]


def get_quality_test_data() -> list[dict]:
    """
    Return test data with various quality levels for model comparison.
    Includes good translations and different types of errors.
    """
    return [
        # === GOOD TRANSLATIONS ===
        {
            "src": "오늘 날씨가 정말 좋습니다.",
            "mt": "The weather is really nice today.",
            "quality": "good",
            "error_type": None,
        },
        {
            "src": "이 제품은 품질이 우수하고 가격도 합리적입니다.",
            "mt": "This product has excellent quality and reasonable price.",
            "quality": "good",
            "error_type": None,
        },
        # === MISTRANSLATION (wrong meaning) ===
        {
            "src": "오늘 날씨가 정말 좋습니다.",
            "mt": "Today's food is really delicious.",  # weather -> food
            "quality": "bad",
            "error_type": "mistranslation",
        },
        {
            "src": "그는 회사를 떠났습니다.",
            "mt": "He joined the company.",  # left -> joined (opposite)
            "quality": "bad",
            "error_type": "mistranslation",
        },
        # === UNDERTRANSLATION (missing content) ===
        {
            "src": "서울은 한국의 수도이며 인구가 천만 명이 넘는 대도시입니다.",
            "mt": "Seoul is the capital of Korea.",  # missing population info
            "quality": "bad",
            "error_type": "undertranslation",
        },
        {
            "src": "회의는 오전 10시에 시작하여 오후 3시에 끝났습니다.",
            "mt": "The meeting started at 10 AM.",  # missing end time
            "quality": "bad",
            "error_type": "undertranslation",
        },
        # === OVERTRANSLATION (added content) ===
        {
            "src": "사과가 맛있습니다.",
            "mt": "The red and fresh apple from the orchard is very delicious and sweet.",
            "quality": "bad",
            "error_type": "overtranslation",
        },
        # === GRAMMAR ERRORS ===
        {
            "src": "그녀는 어제 학교에 갔습니다.",
            "mt": "She go to school yesterday.",  # wrong tense
            "quality": "bad",
            "error_type": "grammar",
        },
        {
            "src": "그들은 새 차를 샀습니다.",
            "mt": "They buyed a new car.",  # buyed -> bought
            "quality": "bad",
            "error_type": "grammar",
        },
        # === LITERAL/AWKWARD TRANSLATION ===
        {
            "src": "눈이 높다",  # idiom: have high standards
            "mt": "Eyes are high.",  # literal, wrong
            "quality": "bad",
            "error_type": "literal",
        },
        {
            "src": "발이 넓다",  # idiom: know many people
            "mt": "Feet are wide.",  # literal, wrong
            "quality": "bad",
            "error_type": "literal",
        },
        # === COMPLETELY WRONG / UNRELATED ===
        {
            "src": "인공지능은 미래 기술의 핵심입니다.",
            "mt": "I like pizza and hamburgers.",  # unrelated
            "quality": "bad",
            "error_type": "unrelated",
        },
        # === EMPTY / GIBBERISH ===
        {
            "src": "컴퓨터가 고장났습니다.",
            "mt": "",  # empty
            "quality": "bad",
            "error_type": "empty",
        },
        {
            "src": "내일 비가 올 것 같습니다.",
            "mt": "asdf jkl; qwer uiop zxcv",  # gibberish
            "quality": "bad",
            "error_type": "gibberish",
        },
    ]


def print_results(data: list[dict], scores: list[float], system_score: float, model_name: str):
    """Print evaluation results."""
    print(f"\n{'=' * 60}")
    print(f"{model_name} Evaluation Results")
    print("=" * 60)

    for i, (item, score) in enumerate(zip(data, scores)):
        print(f"\n[{i+1}] Source: {item['src']}")
        print(f"    Translation: {item['mt']}")
        print(f"    Score: {score:.4f}")

    print(f"\n{'=' * 60}")
    print(f"System Score (average): {system_score:.4f}")
    print("=" * 60)
