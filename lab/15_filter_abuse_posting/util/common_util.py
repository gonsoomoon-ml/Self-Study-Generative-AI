from pprint import pprint
import json

def show_json_product_details(df, row=0, col="product_details"):
    """JSON 뷰어 - 단일 행
    show_json_product_details(df, row=0)
    """
    print(f"\n행 {row}:"); pprint(json.loads(str(df.iloc[row][col])), indent=2)



def show_json(df, row):
    """전체 행 데이터 출력 (product_details는 예쁘게 출력)"""
    print(f"\n행 {row}:")
    row_data = df.iloc[row].to_dict()
    
    for col, value in row_data.items():
        if col == "product_details":
            print(f"\n{col}:")
            show_json_product_details(df, row, col)
        else:
            print(f"{col}: {value}")


