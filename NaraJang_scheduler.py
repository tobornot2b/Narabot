import requests
import pandas as pd
import telegram
from datetime import datetime
import sys

# 시간 마다 알람 지정용
from apscheduler.schedulers.blocking import BlockingScheduler


# 요청url 잘게 자르기
url1 = 'http://apis.data.go.kr/1230000/BidPublicInfoService02'  # 입찰조회
url2 = 'http://apis.data.go.kr/1230000/ScsbidInfoService'  # 낙찰조회

operation_name1 = (
    '/getBidPblancListInfoThngPPSSrch'  # 오퍼레이션명(나라장터검색조건에 의한 입찰공고물품조회) 1.입찰공고
)
operation_name2 = (
    '/getOpengResultListInfoThngPPSSrch'  # 오퍼레이션명(나라장터 검색조건에 의한 개찰결과 물품 목록 조회) 2.개찰결과
)
operation_name3 = (
    '/getScsbidListSttusThngPPSSrch'  # 오퍼레이션명(나라장터 검색조건에 의한 낙찰된 목록 현황 물품조회) 3.낙찰목록
)
# operation_name4 = '/getOpengResultListInfoOpengCompt' # 오퍼레이션명(개찰결과 개찰완료 목록 조회) 4.투찰업체정보
# operation_name5 = '/getOpengResultListInfoThngPreparPcDetail' # 오퍼레이션명(개찰결과 물품 예비가격상세 목록 조회) 5.예비가격


# 요청 파라메터
inqryDiv1 = '?inqryDiv=1'  # 조회구분 (1:공고게시일시 2:입찰공고번호) 입찰공고는 1이 기본. 개찰이후는 2가 기본
inqryDiv2 = '?inqryDiv=2'  # 조회구분 (1:공고게시일시 2:개찰일시 3:입찰공고번호) 입찰공고는 1이 기본. 개찰이후는 2가 기본
# inqryDiv3 = '?inqryDiv=3' # 조회구분 (1:공고게시일시 2:개찰일시 3:입찰공고번호) 입찰공고는 1이 기본. 개찰이후는 2가 기본

numOfRows = '&numOfRows=100'  # 한 페이지 결과 수
pageNo = '&pageNo=1'  # 페이지 번호
rt_type = '&type=json'  # 자료리턴 타입
inqryBgnDt = '&inqryBgnDt=' + datetime.today().strftime('%Y%m%d') + '0000'  # 조회시작일시
# inqryBgnDt = '&inqryBgnDt=' + '20211220' + '0000' # 조회시작일시
inqryEndDt = '&inqryEndDt=' + datetime.today().strftime('%Y%m%d') + '2359'  # 조회종료일시
inqrybidNtceNm = '&bidNtceNm=교복'  # 입찰공고명
# inqrybidNtceNo = '&bidNtceNo=20211103588' # 입찰공고번호

# 키 가져오기
sys.path.append('/settings')
import config
serviceKey = config.API_Keys['data_go_kr_Key']

# 입찰공고 URL
url_assemble1 = (
    url1
    + operation_name1
    + inqryDiv1
    + inqryBgnDt
    + inqryEndDt
    + pageNo
    + numOfRows
    + inqrybidNtceNm
    + rt_type
    + serviceKey
)

# 개찰결과 URL
url_assemble2 = (
    url2
    + operation_name2
    + inqryDiv2
    + inqryBgnDt
    + inqryEndDt
    + pageNo
    + numOfRows
    + inqrybidNtceNm
    + rt_type
    + serviceKey
)

# 낙찰목록 URL
url_assemble3 = (
    url2
    + operation_name3
    + inqryDiv2
    + inqryBgnDt
    + inqryEndDt
    + pageNo
    + numOfRows
    + inqrybidNtceNm
    + rt_type
    + serviceKey
)


# 텔레그램 봇 생성
token = config.TELEGRAM_API_Keys['token']
bot = telegram.Bot(token)
t_id = config.TELEGRAM_API_Keys['telegram_id']  # 채널

info_message = '''1시간 주기로 데이터를 가져옵니다.
입찰명 검색어는 "교복" 으로 설정되어 있습니다. '''

# 오늘 날짜
today = datetime.today().strftime('%Y-%m-%d %H:%M:%S')


# 스케줄러 생성 (타임존 설정 안하면 warning 뜸)
sched = BlockingScheduler(timezone='Asia/Seoul')


# 데이터 추출 parser
def json_parse(gbn):
    try:
        # parsing 하기
        if gbn == 1:
            result = requests.get(url_assemble1)
        elif gbn == 2:
            result = requests.get(url_assemble2)
        elif gbn == 3:
            result = requests.get(url_assemble3)

        result_data = result.json()
        df = pd.json_normalize(result_data['response']['body']['items'])

        if gbn == 1:
            # 열 값 바꾸기 (분할 후 병합)
            df['지역'] = df['ntceInsttNm'].str[:2]
            name_split = df['ntceInsttNm'].str.split(' ')
            df['ntceInsttNm'] = name_split.str.get(-1)
            df['ntceInsttNm'] = df['ntceInsttNm'].str[:-2]

            # 원하는 열만 뽑아내기
            df = df[
                [
                    'bidNtceNo',  # 입찰공고번호
                    'bidNtceOrd',  # 입찰공고차수
                    'ntceKindNm',  # 공고종류명
                    '지역',  # 위에서 새로만든 컬럼
                    'ntceInsttNm',  # 공고기관명
                    'bidBeginDt',  # 입찰개시일시
                ]
            ]

            # 열이름 한글변경
            df.columns = ['공고번호', '차수', '공고종류', '지역', '학교', '입찰개시일']

        elif gbn == 2:
            # 열 값 바꾸기 (분할 후 병합)
            df['지역'] = df['dminsttNm'].str[:2]
            name_split = df['dminsttNm'].str.split(' ')
            df['dminsttNm'] = name_split.str.get(-1)
            df['dminsttNm'] = df['dminsttNm'].str[:-2]

            # 원하는 열만 뽑아내기
            df = df[
                [
                    'bidNtceNo',  # 입찰공고번호
                    'bidNtceOrd',  # 입찰공고차수
                    '지역',  # 위에서 새로만든 컬럼
                    'dminsttNm',  # 수요기관명
                    'prtcptCnum',  # 업체수
                    'progrsDivCdNm',  # 진행구분코드명
                ]
            ]

            # 열이름 한글변경
            df.columns = ['공고번호', '차수', '지역', '학교', '업체수', '상태구분']

        elif gbn == 3:
            # 열 값 바꾸기 (분할 후 병합)
            df['지역'] = df['dminsttNm'].str[:2]
            name_split = df['dminsttNm'].str.split(' ')
            df['dminsttNm'] = name_split.str.get(-1)
            df['dminsttNm'] = df['dminsttNm'].str[:-2]

            # 원하는 열만 뽑아내기
            df = df[
                [
                    'bidNtceNo',  # 입찰공고번호
                    'bidNtceOrd',  # 입찰공고차수
                    'prtcptCnum',  # 업체수
                    '지역',  # 위에서 새로만든 컬럼
                    'dminsttNm',  # 수요기관명
                    'bidwinnrNm',  # 최종낙찰업체명
                    'sucsfbidAmt',  # 최종낙찰금액
                    'sucsfbidRate',  # 최종낙찰률
                    'fnlSucsfDate',  # 최종낙찰일자
                ]
            ]

            # 열이름 한글변경
            df.columns = [
                '공고번호',
                '차수',
                '업체수',
                '지역',
                '학교',
                '낙찰업체',
                '낙찰금액',
                '낙찰률',
                '낙찰일자',
            ]

        df.index = df.index + 1
        return df

        # 열 정렬
        # with pd.option_context('display.max_rows', None, 'display.max_columns', None):

    except Exception as e:
        print(f'{gbn}번 수행 중 알 수 없는 에러가 발생하였습니다.')
        print(e)


def send_list():
    try:
        bot.sendMessage(chat_id=t_id, text=info_message)
        # 입찰공고
        gongo = json_parse(1)

        # 총 건수
        num = str(len(gongo.index))

        # 현재시각
        t_day = datetime.today().strftime('%m-%d %H:%M:%S')

        # 본문 표
        gongo = gongo.to_markdown()

        print(gongo)
        bot.send_message(chat_id=t_id, text='{}'.format(gongo), parse_mode='Markdown')

        bot.sendMessage(
            chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 입찰공고 총 {num} 건 입니다. (공고게시일 기준)'
        )
    except AttributeError:
        bot.sendMessage(
            chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 입찰공고 총 0 건 입니다. (공고게시일 기준)'
        )
    except Exception as e:
        print('입찰공고 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)

    try:
        # 개찰결과
        gaechal = json_parse(2)

        # 총 건수
        num = str(len(gaechal.index))

        # 현재시각
        t_day = datetime.today().strftime('%m-%d %H:%M:%S')

        # 본문 표
        gaechal = gaechal.to_markdown()
        print(gaechal)
        bot.send_message(chat_id=t_id, text=f'{gaechal}', parse_mode='Markdown')

        bot.sendMessage(
            chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 개찰결과 총 {num} 건 입니다. (개찰일 조회기준)'
        )
    except AttributeError:
        bot.sendMessage(
            chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 개찰결과 총 0 건 입니다. (개찰일 조회기준)'
        )
    except Exception as e:
        print('개찰결과 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)


if __name__ == '__main__':
    # 최초 시작
    send_list()

    # 스케줄 설정
    # 수행방식은 3가지가 있습니다
    # Cron 방식 - Cron 표현식으로 수행
    # Date 방식 - 특정 날짜에 수행
    # Interval 방식 - 일정 주기로 수행

    # 1시간 마다 해당 코드 반복 실행
    # cron 매시간 59분 10초에 실행한다는 의미.
    # sched.add_job(send_list, 'cron', minute='59', second='10', id='test_11')
    # sched.add_job(send_list, 'interval', seconds=30)
    
    sched.add_job(
        send_list,
        'interval',
        hours=3,
        start_date=f'{today}',
        end_date=f'{today[:10]} 18:00:00'
    )

    # 시작
    sched.start()
