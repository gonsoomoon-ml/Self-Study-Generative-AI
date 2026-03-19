## 배경
사용하고 있는 Claude Code 는 Backend 가 Amazon Bedrock 에 연결이 되어서, API Usage 형태로 과금이 되고 있습니다.
사용자마다 과다 사용으로 인해서, 특정 금액의 사용이 도달이 되면, Claude Code 사용을 중지하는 것이 필요 합니다.

## 구현 아이디어
Claude Code 의 Custom Plugin 을 사용해서, 이 기능의 구현이 가능할까요?
예를 들어서, Custom Plugin 는 AWS 의 Claude Code 의 Bedrcok 과금을 주기적으로 확인을 해서, 특정 금액이 도달을 하면, 사용 중단을 하게 합니다. 


