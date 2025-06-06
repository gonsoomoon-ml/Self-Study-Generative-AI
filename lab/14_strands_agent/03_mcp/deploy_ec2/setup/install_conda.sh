#!/bin/bash

# Miniconda 설치 스크립트
echo "Miniconda 설치를 시작합니다..."

# Miniconda 설치 파일 다운로드
echo "Miniconda 설치 파일을 다운로드합니다..."
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh

# 설치 스크립트 실행
echo "Miniconda를 설치합니다..."
bash miniconda.sh -b -p $HOME/miniconda

# 환경 변수 설정
echo "환경 변수를 설정합니다..."
echo 'export PATH="$HOME/miniconda/bin:$PATH"' >> ~/.bashrc

# conda 초기화 및 환경 변수 적용
echo "conda를 초기화합니다..."
$HOME/miniconda/bin/conda init bash
source ~/.bashrc

# 설치 확인
echo "Miniconda 설치를 확인합니다..."
$HOME/miniconda/bin/conda --version

# 임시 파일 정리
echo "임시 파일을 정리합니다..."
rm miniconda.sh

echo "Miniconda 설치가 완료되었습니다!"
echo "자주 사용하는 conda 명령어:"
echo "1. 가상환경 생성: conda create -n 환경이름 python=버전"
echo "2. 가상환경 활성화: conda activate 환경이름"
echo "3. 가상환경 비활성화: conda deactivate"
echo "4. 설치된 가상환경 목록 보기: conda env list"
echo "5. 패키지 설치: conda install 패키지이름"
echo "6. 가상환경 삭제: conda env remove -n 환경이름"
echo "7. conda 업데이트: conda update conda"