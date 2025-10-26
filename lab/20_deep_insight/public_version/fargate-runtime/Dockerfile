FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
RUN apt-get update && apt-get install -y \
    # 한글 폰트
    fonts-nanum \
    # 폰트 관리
    fontconfig \
    # pandoc과 texlive (문서 변환용)
    pandoc \
    texlive \
    texlive-xetex \
    texlive-fonts-recommended \
    # PDF 처리
    poppler-utils \
    # 기타 유용한 도구
    curl \
    && rm -rf /var/lib/apt/lists/*

# 폰트 캐시 갱신
RUN fc-cache -f -v

# Python 패키지 설치를 위한 requirements.txt 생성
COPY <<EOF requirements.txt
pandas>=2.3.1
matplotlib>=3.10.5
numpy>=1.26.4
boto3>=1.40.10
koreanize-matplotlib>=0.1.1
python-dotenv>=1.1.1
flask>=3.0.0
requests>=2.32.0
seaborn>=0.13.2
pathlib>=1.0.0
lovelyplots>=1.0.2
weasyprint>=66.0
markdown>=3.9
scikit-learn>=1.7.1
pillow>=11.3.0
plotly>=6.3.0
reportlab>=4.4.3
fpdf2>=2.8.4
matplotlib-inline>=0.1.7
EOF

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# matplotlib 폰트 캐시 정리
RUN python -c "import matplotlib.font_manager as fm; fm.get_font_names()" || true

# 애플리케이션 코드 복사
COPY dynamic_executor_v2.py .

# 데이터 파일은 동적 업로드로만 제공됨 (Dockerfile에서 복사하지 않음)

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV ENV_NAME=production
ENV AWS_DEFAULT_REGION=us-east-1

# 컨테이너 실행 시 Python 스크립트 실행
CMD ["python", "-u", "dynamic_executor_v2.py"]