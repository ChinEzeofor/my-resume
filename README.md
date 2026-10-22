# my-resume
This is a resume website project

## Building the resumes

`resume.md` and `resume-automation.md` are the source of truth. Rebuild the Word
versions with:

```bash
pip3 install python-docx           # one-time
python3 md2docx.py resume.md Chinedu_Ezeofor_Resume.docx
python3 md2docx.py resume-automation.md Chinedu_Ezeofor_Resume_Automation.docx
```

Edit the markdown, never the .docx — the .docx is regenerated and overwritten.
