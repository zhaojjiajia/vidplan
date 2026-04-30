from openai import OpenAI

client = OpenAI(
    api_key="sk-zhaojiajiawb-eKhM9EjcBn5bchea7",
    base_url="http://192.168.200.104:8317/v1"
)

resp = client.chat.completions.create(
    model="gpt-5.5-pro",
    messages=[
        {"role": "user", "content": "你好，你是什么模型，是chatgpt pro吗？相比plus有什么优势"}
    ]
)

print(resp.choices[0].message.content)