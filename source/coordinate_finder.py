import requests

# この関数は、指定された住所の緯度と経度をOpenStreetMapのNominatim APIを使用して取得します。
# @param address: 緯度と経度を取得したい住所の文字列
# @return: 住所の緯度と経度をタプルで返します。住所が見つからない場合はNoneを返します。
def get_lat_lng(address):
    # Nominatim APIの基本URL
    base_url = "https://nominatim.openstreetmap.org/search"

    # リクエストヘッダーにユーザーエージェントを設定
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    # リクエストパラメータ。ここで住所と返却形式を指定
    params = {
        'q': address,
        'format': 'json',
    }

    # APIにリクエストを送信
    response = requests.get(base_url, params=params, headers=headers)

    # ステータスコードが200（成功）の場合、結果を処理
    if response.status_code == 200:
        results = response.json()
        # 結果が空でない場合、最初の結果の緯度と経度を返す
        if results:
            return (float(results[0]['lat']), float(results[0]['lon']))
        else:
            return None
    else:
        # ステータスコードが200以外の場合、エラーを発生させる
        raise Exception(f"Error: {response.status_code}")

# debug用、無視していい
def main():
    # 緯度と経度を取得したい住所
    address = "町田駅"

    # get_lat_lng関数を呼び出して緯度と経度を取得
    lat_lng = get_lat_lng(address)
    if lat_lng:
        print(f"Latitude: {lat_lng[0]}, Longitude: {lat_lng[1]}")
    else:
        print("Location not found.")

# debug用、無視していい
if __name__ == "__main__":
    main()
