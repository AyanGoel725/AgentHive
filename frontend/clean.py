import os

files_to_remove = [
    'src/components/AgentStatus.tsx',
    'src/components/VoiceButton.tsx',
    'src/components/ChatPanel.tsx',
    'src/components/OutputDisplay.tsx'
]

for f in files_to_remove:
    path = os.path.join(os.getcwd(), f.replace('/', os.sep))
    try:
        os.remove(path)
        print(f"Removed {path}")
    except OSError as e:
        print(f"Error removing {path}: {e}")
