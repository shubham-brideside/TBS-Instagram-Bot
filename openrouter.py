from openai import OpenAI

def main():
    client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
    )

    completion = client.chat.completions.create(
    extra_headers={
        "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
        "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    },
    extra_body={},
    model="google/gemini-2.0-flash-exp:free",
    messages=[
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": "What is in this image?"
            },
            {
            "type": "image_url",
            "image_url": {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
            }
            }
        ]
        }
    ]
    )
    print(completion.choices[0].message.content)

if __name__ == "__main__":
    main()