import requests
import pandas as pd
import telegram
from telegram.ext import Updater # 명령어 감지
from telegram.ext import MessageHandler, Filters  # 명령어 감지
from datetime import datetime
import sys
from tabulate import tabulate # 표 프린트

# 시간 마다 알람 지정용
from apscheduler.schedulers.blocking import BlockingScheduler


# 키 가져오기
sys.path.append('c:/settings')
import config
serviceKey = config.API_Keys['data_go_kr_Key']


# 텔레그램 봇 생성
token = config.TELEGRAM_API_Keys['token']
bot = telegram.Bot(token)
t_id = config.TELEGRAM_API_Keys['telegram_id']  # 채널
interv_num = 4 # 시간 or 분 인터벌
interv_num2 = 4 # 시간 or 분 인터벌 (체육복)
words = ['교복', '학생복', '생활복', '동복', '하복'] # 검색어 (검색어 조정 시 여기를 수정할 것)
words2 = ['체육복', '후드', '생활복'] # 체육복 검색어
area_filter1 = [ ['서울', '인천', '시흥', '부천', '부평'], [] ] # 체육복 지역 필터링 (서울상권)
area_filter2 = [ ['경기', '강원'], ['시흥', '부천', '부평'] ] # 체육복 지역 필터링 (중부상권)

info_message = f'''{interv_num}시간 주기로 데이터를 가져옵니다.\n
공고명 검색어 : {words}\n
"/명령어"를 입력해서 기능을 확인하세요.'''

info_message2 = f'''체육복 검색을 시작합니다.
{interv_num2}시간 주기로 데이터를 가져옵니다.\n
공고명 검색어 : {words2}
서울상권 키워드 : {area_filter1[0]} 적용
중부상권 키워드 : {area_filter2[0]} 적용 후 {area_filter2[1]} 제외\n
체육복은 csv파일로 제공됩니다.'''


# 오늘 날짜
today = datetime.today().strftime('%Y-%m-%d %H:%M:%S')

# 스케줄러 생성 (타임존 설정 안하면 warning 뜸)
sched = BlockingScheduler(timezone='Asia/Seoul')


def make_query(bid_nos: list = [], contract: list = [], words = words) -> list:
    # 요청url 잘게 자르기
    url1 = 'http://apis.data.go.kr/1230000/BidPublicInfoService04'  # 입찰조회
    url2 = 'http://apis.data.go.kr/1230000/ScsbidInfoService'  # 낙찰조회

    # 오퍼레이션명(나라장터검색조건에 의한 입찰공고물품조회) 1.입찰공고
    operation_name1 = '/getBidPblancListInfoThngPPSSrch01'
    
    # 오퍼레이션명(나라장터 검색조건에 의한 개찰결과 물품 목록 조회) 2.개찰결과
    operation_name2 = '/getOpengResultListInfoThngPPSSrch'
    
    # 오퍼레이션명(나라장터 검색조건에 의한 낙찰된 목록 현황 물품조회) 3.낙찰목록
    operation_name3 = '/getScsbidListSttusThngPPSSrch'
    
    # 오퍼레이션명(개찰결과 개찰완료 목록 조회) 4.투찰업체정보
    operation_name4 = '/getOpengResultListInfoOpengCompt'
    
    # 오퍼레이션명(개찰결과 물품 예비가격상세 목록 조회) 5.예비가격
    operation_name5 = '/getOpengResultListInfoThngPreparPcDetail'


    # 요청 파라메터
    inqryDiv1 = '?inqryDiv=1'  # 조회구분 (1:공고게시일시 2:입찰공고번호) 입찰공고는 1이 기본. 개찰이후는 2가 기본
    inqryDiv2 = '?inqryDiv=2'  # 조회구분 (1:공고게시일시 2:개찰일시 3:입찰공고번호) 입찰공고는 1이 기본. 개찰이후는 2가 기본
    inqryDiv3 = '?inqryDiv=3'  # 조회구분 (1:공고게시일시 2:개찰일시 3:입찰공고번호) 입찰공고는 1이 기본. 개찰이후는 2가 기본
    inqryDiv4 = '?inqryDiv=4'

    numOfRows = '&numOfRows=100'  # 한 페이지 결과 수
    pageNo = '&pageNo=1'  # 페이지 번호
    rt_type = '&type=json'  # 자료리턴 타입
    inqryBgnDt = '&inqryBgnDt=' + datetime.today().strftime('%Y%m%d') + '0000'  # 조회시작일시
    # inqryBgnDt = '&inqryBgnDt=' + '20221201' + '0000' # 조회시작일시
    inqryEndDt = '&inqryEndDt=' + datetime.today().strftime('%Y%m%d') + '2359'  # 조회종료일시
    inqrybidNtceNm = '&bidNtceNm='  # 입찰공고명
    inqrybidNtceNo = '&bidNtceNo=' # 입찰공고번호


    # 나라장터검색조건에 의한 계약현황 물품조회 (위의 변수들과 명칭이 달라 호환불가)
    url3 = 'http://apis.data.go.kr/1230000/CntrctInfoService'
    operation_name6 = '/getCntrctInfoListThngPPSSrch'
    inqryBgnDt2 = '&inqryBgnDate=' + datetime.today().strftime('%Y%m%d')  # 조회시작일시
    inqryEndDt2 = '&inqryEndDate=' + datetime.today().strftime('%Y%m%d')  # 조회종료일시
    inqrybidNtceNm2 = '&prdctClsfcNoNm=교복' # 품명 (검색어)
    bid_method = '&cntrctMthdCd=' # 계약방법코드


    url_list1 = [] # 입찰공고
    url_list2 = [] # 개찰결과
    url_list3 = [] # 낙찰조회
    url_list4 = [] # 계약조회 (일반, 수의)
    url_list_no = []

    if bid_nos: # 입찰번호 제공될때는 처리 후 탈출
        for no in bid_nos:
            url_assemble_no = (
                url2
                + operation_name2
                + inqryDiv3
                # + inqryBgnDt
                # + inqryEndDt
                + pageNo
                + numOfRows
                + inqrybidNtceNo + no
                + rt_type
                + serviceKey
                )
            url_list_no.append(url_assemble_no)
        return url_list_no
    

    for word in words:
        # 입찰공고 URL
        url_assemble1 = (
            url1
            + operation_name1
            + inqryDiv1 # 1:공고게시일시, 2:개찰일시
            + inqryBgnDt
            + inqryEndDt
            + pageNo
            + numOfRows
            + inqrybidNtceNm + word
            + rt_type
            + serviceKey
            )

        # 개찰결과 URL
        url_assemble2 = (
            url2
            + operation_name2
            + inqryDiv2 # 1:공고일시, 2:개찰일시, 3:입찰공고번호
            + inqryBgnDt
            + inqryEndDt
            + pageNo
            + numOfRows
            + inqrybidNtceNm + word
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
            + inqrybidNtceNm + word
            + rt_type
            + serviceKey
            )
        
        url_list1.append(url_assemble1)
        url_list2.append(url_assemble2)
        url_list3.append(url_assemble3)

    
    # 나라장터검색조건에 의한 계약현황 물품조회 URL
    if contract: # 계약검색조건 ([1, 4]) 제공될때는 처리 후 탈출
        for l in contract: # 1:일반경쟁, 4:수의계약
            url_assemble4 = (
                url3
                + operation_name6
                + inqryDiv1 # 1:계약체결일자, 2:확정계약번호, 3:요청번호, 4:공고번호 (품명검색은 1번만 가능하다)
                + inqryBgnDt2
                + inqryEndDt2
                + pageNo
                + numOfRows
                + inqrybidNtceNm2
                + bid_method + l
                + rt_type
                + serviceKey
                )

            url_list4.append(url_assemble4)
        return url_list4

    return url_list1, url_list2, url_list3


def json_parse(gbn: int, urls: list) -> pd.DataFrame:
    df_result = pd.DataFrame()
    try:
        # parsing 하기
        for i, url in enumerate(urls):
            result = requests.get(url)
            result_data = result.json()

            if result_data['response']['body']['totalCount'] == 0:
                print(f'리스트의 {i+1}번째 URL 조회결과가 없어서 다음으로 넘어간다.')
                continue
            
            df = pd.json_normalize(result_data['response']['body']['items'])
            # print(df)

            if gbn == 1:
                # 열 값 바꾸기 (분할 후 병합)
                df['지역'] = df['ntceInsttNm'].str[:2]
                name_split = df['ntceInsttNm'].str.split(' ')
                df['ntceInsttNm'] = name_split.str.get(-1)
                df['ntceInsttNm'] = df['ntceInsttNm'].str[:-2]

                # 원하는 열만 뽑아내기
                df = df[[
                        'bidNtceNo',  # 입찰공고번호
                        'bidNtceOrd',  # 입찰공고차수
                        'ntceKindNm',  # 공고종류명
                        '지역',  # 위에서 새로만든 컬럼
                        'ntceInsttNm',  # 공고기관명
                        'bidBeginDt',  # 입찰개시일시
                        ]]

                # 열이름 한글변경
                df.columns = ['공고번호', '차수', '공고종류', '지역', '학교', '입찰개시일']

            elif gbn == 2:
                # 열 값 바꾸기 (분할 후 병합)
                df['지역'] = df['dminsttNm'].str[:2]
                name_split = df['dminsttNm'].str.split(' ')
                df['dminsttNm'] = name_split.str.get(-1)
                df['dminsttNm'] = df['dminsttNm'].str[:-2]

                # 원하는 열만 뽑아내기
                df = df[[
                    'bidNtceNo',  # 입찰공고번호
                    'bidNtceOrd',  # 입찰공고차수
                    '지역',  # 위에서 새로만든 컬럼
                    'dminsttNm',  # 수요기관명
                    'prtcptCnum',  # 업체수
                    'progrsDivCdNm',  # 진행구분코드명
                    ]]

                # 열이름 한글변경
                df.columns = ['공고번호', '차수', '지역', '학교', '업체수', '상태구분']

            elif gbn == 3:
                # 열 값 바꾸기 (분할 후 병합)
                df['지역'] = df['dminsttNm'].str[:2]
                name_split = df['dminsttNm'].str.split(' ')
                df['dminsttNm'] = name_split.str.get(-1)
                df['dminsttNm'] = df['dminsttNm'].str[:-2]

                # 원하는 열만 뽑아내기
                df = df[[
                    'bidNtceNo',  # 입찰공고번호
                    'bidNtceOrd',  # 입찰공고차수
                    'prtcptCnum',  # 업체수
                    '지역',  # 위에서 새로만든 컬럼
                    'dminsttNm',  # 수요기관명
                    'bidwinnrNm',  # 최종낙찰업체명
                    'sucsfbidAmt',  # 최종낙찰금액
                    'sucsfbidRate',  # 최종낙찰률
                    'fnlSucsfDate',  # 최종낙찰일자
                    ]]

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
            
            elif gbn == 4: # 계약조회
                name_split = df['cntrctInsttNm'].str.split(' ')
                df['cntrctInsttNm'] = name_split.str.get(-1)
                df['cntrctInsttNm'] = df['cntrctInsttNm'].str[:-2]

                df = df[[
                    'dcsnCntrctNo',  # 확정계약번호
                    'cntrctCnclsMthdNm',  # 계약체결방법명
                    'cntrctInsttNm',  # 계약기관명
                    'cntrctDtlInfoUrl',  # 계약상세정보URL
                    ]]

                df.columns = [
                    '계약번호',
                    '계약형태',
                    '학교명',
                    '상세URL',
                    ]

            df_result = pd.concat([df_result, df])
        
        df_result = df_result.drop_duplicates()
        df_result = df_result.reset_index(drop=True)
        df_result.index = df_result.index + 1
        
        return df_result

        # 열 정렬
        # with pd.option_context('display.max_rows', None, 'display.max_columns', None):

    except Exception as e:
        print(f'{url}\n수행 중 알 수 없는 에러가 발생하였습니다.')
        print(e)


def json_parse2(gbn: int, urls: list, filter: list) -> pd.DataFrame: # 체육복용
    df_result = pd.DataFrame()
    try:
        for i, url in enumerate(urls):
            result = requests.get(url)
            result_data = result.json()
            if result_data['response']['body']['totalCount'] == 0:
                print(f'리스트의 {i+1}번째 URL 조회결과가 없어서 다음으로 넘어간다.')
                continue
            df = pd.json_normalize(result_data['response']['body']['items'])

            if gbn == 1:
                # 원하는 열만 뽑아내기
                df = df[[
                        'bidNtceNo',  # 입찰공고번호
                        'bidNtceOrd',  # 입찰공고차수
                        'ntceKindNm',  # 공고종류명
                        'bidNtceDt',  # 입찰공고일시
                        'bidNtceNm',  # 입찰공고명
                        'ntceInsttNm',  # 공고기관명
                        'cntrctCnclsMthdNm', # 계약체결방법명
                        'bidBeginDt',  # 입찰개시일시
                        'bidClseDt',  # 입찰마감일시
                        'opengDt',  # 개찰일시
                        'asignBdgtAmt',  # 배정예산금액
                        'bidNtceDtlUrl',  # 입찰공고상세URL
                        'prdctQty',  # 물품수량
                        'rgstDt',  # 등록일시
                        ]]

                # 열이름 한글변경
                df.columns = [
                    '입찰공고번호', '입찰공고차수', '공고종류명', '입찰공고일시', '입찰공고명',
                    '공고기관명', '계약체결방법명', '입찰개시일시', '입찰마감일시', '개찰일시',
                    '배정예산금액', '입찰공고상세URL', '물품수량', '등록일시'
                    ]

                df['공고기관명'] = df['공고기관명'].str.replace('교육청', '').str.replace('교육지원청', '').str.replace('교육지원청', '').str.replace('교육과학기술부', '').str.replace('교육부', '')
                df['지역'] = df['공고기관명'].str.split(' ').str[:-1].str.join(' ')
                df['학교'] = df['공고기관명'].str.split(' ').str[-1].str.replace('등학교', '').str.replace('중학교', '중')
                df1 = df[df['공고기관명'].str.contains('|'.join(filter[0]), na=False)] # 지역필터링(join 함수는 리스트를 문자열로 변환, na=False는 NaN값을 제외하고 검색)
                if len(filter[1]) != 0:
                    df1 = df1[~df1['공고기관명'].str.contains('|'.join(filter[1]))] # 2차필터링 (제외할 것들)
                df1 = df1.drop(['공고기관명'], axis=1)

            elif gbn == 2:
                # 원하는 열만 뽑아내기
                df = df[[
                    'bidNtceNo',  # 입찰공고번호
                    'bidNtceOrd',  # 입찰공고차수
                    'bidNtceNm',  # 입찰공고명
                    'opengDt',  # 개찰일시
                    'prtcptCnum',  # 참가업체수
                    'opengCorpInfo',  # 개찰업체정보
                    'progrsDivCdNm',  # 진행구분코드명
                    'inptDt',  # 입력일시
                    'dminsttNm',  # 수요기관명
                    ]]

                # 열이름 한글변경
                df.columns = ['입찰공고번호', '입찰공고차수', '입찰공고명', '개찰일시', '참가업체수', '개찰업체정보', '진행구분코드명', '입력일시', '수요기관명']
                sep = df['개찰업체정보'].str.split('^')
                df['1위_업체명'] = sep.str[0]
                # df['사업자등록번호'] = sep.str[1]
                # df['대표자'] = sep.str[2]
                df['투찰금액'] = sep.str[3]
                df['투찰율'] = sep.str[4]
                df = df.drop(['개찰업체정보'], axis=1)
                df = df[[
                    '입찰공고번호', '입찰공고차수', '입찰공고명', '개찰일시', '참가업체수',
                    '1위_업체명', '투찰금액', '투찰율',
                    '진행구분코드명', '입력일시', '수요기관명'
                ]]
                
                df['수요기관명'] = df['수요기관명'].str.replace('교육청', '').str.replace('교육지원청', '').str.replace('교육지원청', '').str.replace('교육과학기술부', '').str.replace('교육부', '')
                df['지역'] = df['수요기관명'].str.split(' ').str[:-1].str.join(' ')
                df['학교'] = df['수요기관명'].str.split(' ').str[-1].str.replace('등학교', '').str.replace('중학교', '중')
                df1 = df[df['수요기관명'].str.contains('|'.join(filter[0]), na=False)] # 지역필터링(join 함수는 리스트를 문자열로 변환, na=False는 NaN값을 제외하고 검색)
                if len(filter[1]) != 0:
                    df1 = df1[~df1['수요기관명'].str.contains('|'.join(filter[1]))] # 2차필터링 (제외할 것들)
                df1 = df1.drop(['수요기관명'], axis=1)

            df_result = pd.concat([df_result, df1])
        
        df_result = df_result.drop_duplicates()
        df_result = df_result.reset_index(drop=True)
        df_result.index = df_result.index + 1
        
        return df_result
    except Exception as e:
        print(f'{url}\n수행 중 알 수 없는 에러가 발생하였습니다.')
        print(e)


def send_list():
    try:
        bot.sendMessage(chat_id=t_id, text=info_message)
        urls1, urls2, urls3 = make_query() # 입찰공고
        gongo = json_parse(1, urls1)
        t_day = datetime.today().strftime('%m-%d %H:%M:%S') # 현재시각
        if gongo is not None:
            num = str(len(gongo.index)) # 총 건수
            # gongo = gongo.to_markdown() # 본문 표
            print(gongo)
            bot.send_message(chat_id=t_id, text='{}'.format(gongo), parse_mode='Markdown')
            # bot.send_message(chat_id=t_id, text='{}'.format(tabulate(gongo, tablefmt="plain", showindex="always")), parse_mode='Markdown')
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 입찰공고 총 {num} 건 입니다. (공고게시일 기준)')
        else:
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 오늘은 입찰공고가 아직 없습니다.')
    except AttributeError:
        bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 입찰공고 총 0 건 입니다. (공고게시일 기준)')
    except Exception as e:
        print('입찰공고 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)

    try:
        gaechal = json_parse(2, urls2) # 개찰결과
        t_day = datetime.today().strftime('%m-%d %H:%M:%S') # 현재시각
        if gaechal is not None:
            num = str(len(gaechal.index)) # 총 건수
            # gaechal = gaechal.to_markdown() # 본문 표
            print(gaechal)
            bot.send_message(chat_id=t_id, text=f'{gaechal}', parse_mode='Markdown')
            # bot.send_message(chat_id=t_id, text=f'{tabulate(gaechal, tablefmt="plain", showindex="always")}', parse_mode='Markdown')
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 개찰결과 총 {num} 건 입니다. (개찰일 조회기준)')
        else:
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 오늘은 개찰결과가 아직 없습니다.')
    except AttributeError:
        bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 개찰결과 총 0 건 입니다. (개찰일 조회기준)')
    except Exception as e:
        print('개찰결과 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)

    try:
        pass
    except AttributeError:
        bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 개찰결과 총 0 건 입니다. (공고번호 조회기준)')
    except Exception as e:
        print('개찰결과 공고번호 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)


def send_list2(): # 체육복용
    try:
        bot.sendMessage(chat_id=t_id, text=info_message2)
        urls1, urls2, urls3 = make_query(words=words2) # 입찰공고
        gongo_seoul = json_parse2(1, urls1, area_filter1) # 서울
        gongo_joongboo = json_parse2(1, urls1, area_filter2) # 중부
        t_day = datetime.today().strftime('%m-%d %H:%M:%S') # 현재시각
        
        if gongo_seoul is not None:
            num = str(len(gongo_seoul.index)) # 총 건수
            print(gongo_seoul)
            if num != '0':
                gongo_seoul.to_csv('gongo_seoul.csv', encoding='utf-8-sig', mode='w') # csv 파일로 저장(mode='w' : 덮어쓰기)
                bot.sendDocument(chat_id=t_id, document=open('gongo_seoul.csv', 'rb')) # 텔레그램에 csv 파일 전송
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 서울상권 체육복 입찰공고 총 {num} 건 입니다. (공고게시일 기준)')
        
        if gongo_joongboo is not None:
            num = str(len(gongo_joongboo.index)) # 총 건수
            print(gongo_joongboo)
            if num != '0':
                gongo_joongboo.to_csv('gongo_joongboo.csv', encoding='utf-8-sig', mode='w') # csv 파일로 저장(mode='w' : 덮어쓰기)
                bot.sendDocument(chat_id=t_id, document=open('gongo_joongboo.csv', 'rb')) # 텔레그램에 csv 파일 전송
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 중부상권 체육복 입찰공고 총 {num} 건 입니다. (공고게시일 기준)')
    except AttributeError:
        bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 체육복 입찰공고 총 0 건 입니다. (공고게시일 기준)')
    except Exception as e:
        print('체육복 입찰공고 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)

    try:
        gaechal_seoul = json_parse2(2, urls2, area_filter1) # 서울
        gaechal_joongboo = json_parse2(2, urls2, area_filter2) # 중부
        t_day = datetime.today().strftime('%m-%d %H:%M:%S') # 현재시각
        
        if gaechal_seoul is not None:
            num = str(len(gaechal_seoul.index)) # 총 건수
            print(gaechal_seoul)
            if num != '0':
                gaechal_seoul.to_csv('gaechal_seoul.csv', encoding='utf-8-sig', mode='w')
                # 텔레그램에 csv 파일 전송
                bot.sendDocument(chat_id=t_id, document=open('gaechal_seoul.csv', 'rb'))
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 서울상권 체육복 개찰결과 총 {num} 건 입니다. (개찰일 조회기준)')
        
        if gaechal_joongboo is not None:
            num = str(len(gaechal_joongboo.index)) # 총 건수
            print(gaechal_joongboo)
            if num != '0':
                gaechal_joongboo.to_csv('gaechal_joongboo.csv', encoding='utf-8-sig', mode='w')
                # 텔레그램에 csv 파일 전송
                bot.sendDocument(chat_id=t_id, document=open('gaechal_joongboo.csv', 'rb'))
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 중부상권 체육복 개찰결과 총 {num} 건 입니다. (개찰일 조회기준)')
        
    except AttributeError:
        bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 금일 체육복 개찰결과 총 0 건 입니다. (개찰일 조회기준)')
    except Exception as e:
        print('체육복 개찰결과 조회중 알 수 없는 에러가 발생하였습니다.')
        print(e)


 
# 사용자가 보낸 메세지를 읽어들이고, 답장을 보내줍니다.
# 아래 함수만 입맛에 맞게 수정해주면 됩니다. 다른 것은 건들 필요없어요.
def handler(update, context):
    user_text = update.message.text # 사용자가 보낸 메세지를 user_text 변수에 저장합니다.
    if user_text == "/명령어":
        bot.send_message(
            chat_id=t_id,
            text='''< 명령어 일람 >
    1. /명령어     -> 명령어 일람
    2. /조회     -> 입찰번호로 개찰결과 조회
    3. /공고     -> 입찰공고 일괄조회 (공고일 기준)
    4. /개찰     -> 개찰결과 일괄조회 (개찰일 기준)
    5. /계약     -> 계약결과 일괄조회 (일반, 수의)
    6. /체육복     -> 체육복 입찰공고, 개찰결과 일괄조회

< '조회' 명령어 사용법 >
    조건 1. \"/조회\" 명령어 뒤에 한 칸 비우고 입찰번호 입력
                (여러개 입력 가능)
    조건 2. 번호는 콤마로 구분
            
    예시 : /조회 입찰번호1, 입찰번호2''') # 답장 보내기
    elif user_text[:3] == "/조회": # 입찰번호 개별조회
        input_bidno = user_text[3:].strip().replace(' ', '').split(',')
        bot.send_message(chat_id=t_id, text=f"{input_bidno}") # 답장 보내기
        bot.send_message(chat_id=t_id, text=f"{json_parse(2, make_query(bid_nos = input_bidno))}") # 답장 보내기
    elif user_text[:3] == "/공고": # 당일 입찰공고 조회
        bot.send_message(chat_id=t_id, text=f"< 검색조건 >\n검색대상: 입찰공고(공고게시일 기준)\n검색어: {words}\n검색일: 오늘")
        urls1, _, _ = make_query() # 입찰공고
        gongo = json_parse(1, urls1)
        if len(gongo.index) > 0:
            t_day = datetime.today().strftime('%m-%d %H:%M:%S') # 현재시각
            num = str(len(gongo.index)) # 총 건수
            print(gongo)
            bot.send_message(chat_id=t_id, text=f'{tabulate(gongo, tablefmt="plain", showindex="always")}')
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 입찰공고 총 {num} 건 입니다.')
        else:
            bot.send_message(chat_id=t_id, text=f'입찰공고가 없습니다.')
    elif user_text[:3] == "/개찰": # 당일 개찰결과 조회
        bot.send_message(chat_id=t_id, text=f"< 검색조건 >\n검색대상: 개찰결과(개찰일 기준 조회)\n검색어: {words}\n검색일: 오늘")
        _, urls2, _ = make_query() # 개찰결과
        gaechal = json_parse(2, urls2) # 개찰결과
        if len(gaechal.index) > 0:   # 개찰결과가 있을 경우
            t_day = datetime.today().strftime('%m-%d %H:%M:%S') # 현재시각
            num = str(len(gaechal.index)) # 총 건수
            print(gaechal)
            bot.send_message(chat_id=t_id, text=f'{tabulate(gaechal, tablefmt="plain", showindex="always")}')
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 개찰결과 총 {num} 건 입니다.')
        else:
            bot.send_message(chat_id=t_id, text=f'개찰결과가 없습니다.')
    elif user_text[:3] == "/계약": # 당일 계약 조회 (일반, 수의)
        bot.send_message(chat_id=t_id, text=f"< 검색조건 >\n계약방법: 일반경쟁, 수의계약\n검색어: 교복\n검색일: 오늘")
        contract = json_parse(4, make_query(bid_nos = [], contract = ['1', '4']))
        if len(contract.index) > 0:
            t_day = datetime.today().strftime('%m-%d %H:%M:%S')
            num = str(len(contract.index))
            print(contract)
            bot.send_message(chat_id=t_id, text=f"{tabulate(contract, tablefmt='plain', showindex='always')}")
            bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 계약결과 총 {num} 건 입니다.')
        else:
            bot.send_message(chat_id=t_id, text=f"> 계약결과가 없습니다.")
    elif user_text == "/체육복": # 체육복 조회
        bot.send_message(chat_id=t_id, text=f"< 검색조건 >\n검색대상: 입찰공고, 개찰결과\n검색어: {words2}\n검색일: 오늘")
        urls1, urls2, _ = make_query(words=words2) # 입찰공고, 개찰결과
        gongo_seoul = json_parse2(1, urls1, area_filter1) # 서울 입찰공고
        gongo_joongboo = json_parse2(1, urls1, area_filter2) # 중부 입찰공고
        gaechal_seoul = json_parse2(2, urls2, area_filter1) # 서울 개찰결과
        gaechal_joongboo = json_parse2(2, urls2, area_filter2) # 중부 개찰결과
        nums = []
        if len(gongo_seoul.index) > 0: # 서울 입찰공고가 있을 경우
            nums.append(str(len(gongo_seoul.index))) # 총 건수
            print(gongo_seoul)
            gongo_seoul.to_csv('gongo_seoul.csv', encoding='utf-8-sig', mode='w') # csv 파일로 저장(mode='w' : 덮어쓰기)
            bot.sendDocument(chat_id=t_id, document=open('gongo_seoul.csv', 'rb')) # 텔레그램에 csv 파일 전송
        else:
            nums.append('0')
        if len(gongo_joongboo.index) > 0:
            nums.append(str(len(gongo_joongboo.index)))
            print(gongo_joongboo)
            gongo_joongboo.to_csv('gongo_joongboo.csv', encoding='utf-8-sig', mode='w')
            bot.sendDocument(chat_id=t_id, document=open('gongo_joongboo.csv', 'rb'))
        else:
            nums.append('0')
        if len(gaechal_seoul.index) > 0:
            nums.append(str(len(gaechal_seoul.index)))
            print(gaechal_seoul)
            gaechal_seoul.to_csv('gaechal_seoul.csv', encoding='utf-8-sig', mode='w')
            bot.sendDocument(chat_id=t_id, document=open('gaechal_seoul.csv', 'rb'))
        else:
            nums.append('0')
        if len(gaechal_joongboo.index) > 0:
            nums.append(str(len(gaechal_joongboo.index)))
            print(gaechal_joongboo)
            gaechal_joongboo.to_csv('gaechal_joongboo.csv', encoding='utf-8-sig', mode='w')
            bot.sendDocument(chat_id=t_id, document=open('gaechal_joongboo.csv', 'rb'))
        else:
            nums.append('0')
        
        t_day = datetime.today().strftime('%m-%d %H:%M:%S')
        bot.sendMessage(chat_id=t_id, text=f'> 현재시각  {t_day} \n> 서울 체육복 입찰공고 {nums[0]} 건\n> 중부 체육복 입찰공고 {nums[1]} 건\n> 서울 체육복 개찰결과 {nums[2]} 건\n> 중부 체육복 개찰결과 {nums[3]} 건 입니다.')

        # tabulate 를 안쓰면 url이 축약됨..
        # 문자열 따옴표 구분에 주의할 것


if __name__ == '__main__':
    # updater
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    updater.start_polling()

    echo_handler = MessageHandler(Filters.text, handler)
    dispatcher.add_handler(echo_handler)
    

    # 최초 시작
    send_list()
    send_list2()

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
        hours=interv_num,
        # minutes=interv_num,
        start_date=f'{today}',
        end_date=f'{today[:10]} 18:00:00'
    )

    sched.add_job(
        send_list2,
        'interval',
        hours=interv_num2,
        # minutes=interv_num,
        start_date=f'{today}',
        end_date=f'{today[:10]} 18:00:00'
    )


    # 시작
    sched.start()
