# Static Identity Provisioning

This directory ships only versioned examples and provisioning notes.

Runtime expects two local operator-provisioned files:

- `state/data/identity/llm_identity.txt`
- `state/data/identity/user_identity.txt`

These runtime files are intentionally ignored by Git. They stay local to the host checkout and are mounted into the app container on OVH via:

```text
/opt/platform/fridadev/state/data -> /app/data
```

Bootstrap from the versioned examples:

```bash
cp -n state/data/identity/llm_identity.example.txt state/data/identity/llm_identity.txt
cp -n state/data/identity/user_identity.example.txt state/data/identity/user_identity.txt
```

Then edit the local `.txt` files with the real static identity content required by the runtime. Do not commit those `.txt` files back to Git.
