import sys
with open(sys.argv[1], 'r') as f:
    chunks = f.read().split('\n---\n')
    for i, chunk in enumerate(chunks):
        with open(f'dist/harmony-manifests/templates/manifest-{i}.yaml', 'w') as out:
            out.write(chunk)
