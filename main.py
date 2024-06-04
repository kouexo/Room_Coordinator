from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
client = OpenAI()
api_key = ""
app = Flask(__name__)
app.secret_key = ""


'''解析結果を受け取ってリスト化'''
def parse_room_descriptions(response_text):
   user_room_descriptions = response_text.split('*')
   room_list = []
   
   for description in user_room_descriptions:
       if description.strip():
           room_info = {}
           lines = description.strip().split('\n')
           
           for line in lines:
               if line.startswith('部屋:'):
                   room_info['room_name'] = line.split(':', 1)[1].strip()
               elif line.startswith('畳数:'):
                   room_info['room_size'] = line.split(':', 1)[1].strip()
               elif line.startswith('部屋の説明:'):
                   room_info['room_description'] = line.split(':', 1)[1].strip()
           
           if room_info:
               room_list.append(room_info)
   
   return room_list
# --------------------------------
'''画像生成(DALLE3)'''
# テキストプロンプトに基づいて画像を生成する関数
def generate_image(prompt):
    # APIエンドポイントにリクエストを送信して画像を生成します
    response = client.images.generate(
        model="dall-e-3",  # APIの現在のバージョンに合わせてモデル名を更新
        prompt=prompt,
        size="1024x1024", #画像サイズを指定1024x1024、1024x1792、1792x1024 
        n=1
    )
    # 生成された画像データのURLを取得
    image_url = response.data[0].url
    return image_url
# --------------------------------------------------
#画像URLとか２回目の生成で邪魔な要素を削除する
@app.route('/clear_all', methods=['POST'])
def clear_all():
    session.pop('room_list', None)
    session.pop('generated_images', None)
    return redirect(url_for('index'))

@app.route('/check_room_list')
def check_room_list():
    room_list_exists = 'room_list' in session
    return jsonify(room_list_exists=room_list_exists)

@app.route('/clear_images', methods=['POST'])
def clear_images():
    session.pop('generated_images', None)
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_room_description = request.form['room_description']
        floor_plan_url = request.form['floor_plan_url']
        print("部屋の説明:", user_room_description)
        print("間取り図のURL:", floor_plan_url)

        model_name = "gpt-4o"
        prompt = "画像の間取りを解析してください。解析以外の出力は不要です。各部屋について'部屋:子供部屋','畳数:6畳''部屋の説明:主寝室は、最も広い部屋であり、通常は大人が使用する寝室です。北側に位置しており、収納スペースが充実しています。'の形で返答すること。各部屋の解析を*で区切ってください。"
        image_url = floor_plan_url
        response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                },
                },
            ],
            }
        ],
        max_tokens=300,
        )
        print(response.choices[0].message.content)

        # APIレスポンスを取得
        response_text = response.choices[0].message.content

    # 部屋の説明をパースしてリスト化
        room_list = parse_room_descriptions(response_text)

    # 結果を表示
        generated_images = []
        for room in room_list:
            prompt = prompt = f"あなたは今、{room['room_name']}と呼ばれる{room['room_size']}の部屋に立っています。部屋の特徴は以下の通りです。{room['room_description']}また、あなたがこの部屋に求める要素は以下の通りです。{user_room_description}部屋の中央に立ち、壁の色や材質、床の材質や色合い、窓からの自然光の入り方、照明器具の配置、家具や装飾品のデザイン、色、材質、配置に注目し、部屋の隅々まで観察してください。実際にその部屋に立っているかのように、部屋の臨場感や雰囲気を感じ取り、あなたが求める要素がどのように反映されているかにも注目してください。以上の情報をもとに、あなたが部屋の中に立っている視点から見た、本物の部屋のような高品質な画像を生成してください。画像は、部屋の詳細やリアルな質感、照明の効果などを忠実に再現し、まるで実際の部屋の写真のような仕上がりにし、あなたが求める要素が適切に取り入れられているようにしてください。"
            image_url = generate_image(prompt)
            generated_images.append(image_url)
            print(f"Generated image URL: {image_url}")
        session['room_list'] = room_list
        session['generated_images'] = generated_images
        return render_template('index.html', room_list=room_list, generated_images=generated_images)
        # return render_template('result.html', room_list=room_list, generated_images=generated_images)
    
    room_list = session.get('room_list')
    generated_images = session.get('generated_images')
    return render_template('index.html', room_list=room_list, generated_images=generated_images)
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
