import json
import anthropic
import time
import sys
import io

# Fix stdout encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_KEY = "sk-cp-OPqmVseIS1d8iyidChRRrL86O8mvfSRntORrdE56ZGRwdQpL_6m7QNfSlo7hM54JSzLUNUz6sbWs-9-gloxNw_C5dPzdStn2e6Y7p36B6m-z-03Hwadgd6c"
BASE_URL = "https://api.minimaxi.com/anthropic"

client = anthropic.Anthropic(base_url=BASE_URL, api_key=API_KEY)

def classify_rumor(text):
    """Use LLM to classify if text is rumor or not"""
    prompt = f"""判断以下微博文本是谣言还是非谣言。只回复谣言或非谣言，不要思考不要解释。

文本：{text}"""

    try:
        message = client.messages.create(
            model="MiniMax-M2.1",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        result_text = None
        for block in message.content:
            if block.type == "text" and block.text:
                result_text = block.text.strip()
        # Parse result
        if result_text:
            if "谣言" in result_text and "非谣言" not in result_text:
                return "谣言"
            elif "非谣言" in result_text:
                return "非谣言"
        return None
    except Exception as e:
        print(f"Error: {e}", flush=True)
        return None

def main():
    # Load data
    with open('E:/rumor_detection/data/processed_crawled.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Total records: {len(data)}", flush=True)

    # Find unclassified records
    unclassified = [i for i, item in enumerate(data) if item.get('label') == '未分类']
    print(f"Unclassified records: {len(unclassified)}", flush=True)

    fixed_count = 0
    error_count = 0

    for i, idx in enumerate(unclassified):
        item = data[idx]
        text = item.get('content', '')[:300]

        result = classify_rumor(text)

        if result:
            data[idx]['label'] = result
            fixed_count += 1
            print(f"[{i+1}/{len(unclassified)}] {text[:40]}... -> {result}", flush=True)
        else:
            error_count += 1

        # Save every 100 records
        if (i + 1) % 100 == 0:
            with open('E:/rumor_detection/data/processed_crawled_fixed.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"--- Progress saved: {fixed_count} fixed, {error_count} errors ---", flush=True)

        time.sleep(0.3)  # Rate limiting

    # Final save
    with open('E:/rumor_detection/data/processed_crawled_fixed.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n=== Done! Fixed {fixed_count} records, {error_count} errors ===", flush=True)

    # Show final distribution
    labels = {}
    for item in data:
        label = item.get('label', 'unknown')
        labels[label] = labels.get(label, 0) + 1
    print("\nFinal label distribution:", flush=True)
    for label, count in sorted(labels.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count}", flush=True)

if __name__ == "__main__":
    main()
