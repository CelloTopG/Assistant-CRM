from assistant_crm.api.social_media_ports import YouTubeIntegration
import requests

def test_youtube():
    integ = YouTubeIntegration()
    print("Channel ID:", integ.credentials.get('channel_id'))
    print("API Key exists:", bool(integ.credentials.get('api_key')))
    print("Access Token exists:", bool(integ.credentials.get('access_token')))

    api_key = integ.credentials.get('api_key')
    channel_id = integ.credentials.get('channel_id')
    access_token = integ.credentials.get('access_token')

    if not channel_id:
        print("ERROR: No channel ID")
        return

    # Test video search
    url = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'part': 'id',
        'channelId': channel_id,
        'maxResults': 3,
        'order': 'date',
        'type': 'video'
    }
    headers = {}

    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
        print("Using OAuth token")
    elif api_key:
        params['key'] = api_key
        print("Using API key")
    else:
        print("ERROR: No authentication method")
        return

    try:
        print("Testing video search...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"Video search status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            videos = data.get('items', [])
            print(f"Videos found: {len(videos)}")

            if videos:
                video_id = videos[0]['id']['videoId']
                print(f"Testing comments for video: {video_id}")

                # Test comment fetching
                comment_url = 'https://www.googleapis.com/youtube/v3/commentThreads'
                comment_params = {
                    'part': 'snippet',
                    'videoId': video_id,
                    'maxResults': 5,
                    'order': 'time'
                }

                if access_token:
                    comment_headers = {'Authorization': f'Bearer {access_token}'}
                else:
                    comment_params['key'] = api_key
                    comment_headers = {}

                comment_response = requests.get(comment_url, params=comment_params, headers=comment_headers, timeout=10)
                print(f"Comment API status: {comment_response.status_code}")

                if comment_response.status_code == 200:
                    comment_data = comment_response.json()
                    comments = comment_data.get('items', [])
                    print(f"Comments found: {len(comments)}")

                    if comments:
                        # Show the most recent comment
                        latest = comments[-1]
                        snippet = latest['snippet']['topLevelComment']['snippet']
                        author = snippet.get('authorDisplayName', 'Unknown')
                        text = snippet.get('textDisplay', '')[:100]
                        published = snippet.get('publishedAt', '')
                        print(f"Latest comment by {author}: {text}... (at {published})")
                    else:
                        print("No comments found on this video")
                else:
                    print(f"Comment API error: {comment_response.text[:200]}")
            else:
                print("No videos found for this channel")
        else:
            print(f"Video API error: {response.text[:300]}")

    except Exception as e:
        print(f"Exception: {e}")

test_youtube()