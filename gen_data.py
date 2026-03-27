from datetime import datetime
import json
from supabase import create_client
import os

url = os.getenv('SUPABASE_URL')
# Use SERVICE_ROLE_KEY to bypass RLS policies
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
supabase = create_client(url, key)
user_id = 'c056c1c5-93ce-4a2b-84b9-3d622d185093'

# 다이어리 17개
diaries = []
for day in range(1, 18):
    diaries.append({
        'user_id': user_id,
        'content': f'2026년 3월 {day}일 일과: 새로운 기술 학습 및 프로젝트 진행',
        'mood': 'productive' if day % 3 == 0 else 'happy',
        'tags': ['기술', '회고'],
        'created_at': f'2026-03-{day:02d}T09:00:00Z',
    })

r = supabase.table('diaries').insert(diaries).execute()
print(f'다이어리: {len(r.data)}개')

# 스크랩 100개
scraps = []
entities_list = [
    ('React', 'Framework'), ('Python', 'Language'), ('Database', 'Technology'),
    ('API', 'Concept'), ('Docker', 'Tool'), ('Kubernetes', 'Platform'),
]
for day in range(1, 18):
    per_day = 6 if day <= 16 else 10
    for i in range(per_day):
        entity, etype = entities_list[(day + i) % len(entities_list)]
        scraps.append({
            'user_id': user_id,
            'title': f'[{day}일] {entity} 기술 스크랩 #{i+1}',
            'content': f'{entity}에 관련된 기술 내용 및 학습 자료입니다.',
            'tags': ['학습', '기술'],
            'source_type': 'WEB',
            'extracted_entities': [
                {'name': entity, 'type': etype},
                {'name': 'Knowledge', 'type': 'Concept'}
            ],
            'extracted_relations': [
                {'source': entity, 'target': 'Knowledge', 'type': 'RELATED_TO'}
            ],
            'summary': f'{entity} 관련 학습 자료',
            'status': 'completed',
            'created_at': f'2026-03-{day:02d}T{10+i:02d}:00:00Z',
        })

r = supabase.table('scraps').insert(scraps).execute()
print(f'스크랩: {len(r.data)}개')
print('✨ 완료!')
