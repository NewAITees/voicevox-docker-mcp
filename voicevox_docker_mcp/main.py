from fastapi_mcp import FastApiMCP
import api  # 先ほど作成したapiモジュールをインポート

# MCPサーバーの初期化
mcp = FastApiMCP(
    api.app,  # 既存のFastAPIアプリを指定
    name="VOICEVOX Speech Synthesis MCP",
    description="VOICEVOXを使用して、テキストから音声を合成するMCPサーバー",
    base_url="http://localhost:50039",  # ベースURLを指定（重要）
)

# MCPサーバーをFastAPIアプリに直接マウント
mcp.mount()

# サーバー起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api.app, host="0.0.0.0", port=50039)
