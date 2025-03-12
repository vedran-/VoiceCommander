from setuptools import setup, find_packages

setup(
    name='Voice Commander',
    version='0.2.2',
    packages=find_packages(),
    install_requires=[
        'pyaudio',
        'pyperclip',
        'vosk',
        'groq',
        'googlesearch-python',
        'selenium'
    ],
    entry_points={
        'console_scripts': [
            'vc=scripts.main:main',
        ],
    },
    author='Night Rider',
    author_email='vmanojlo@gmail.com',
    description='Listens to your microphone and transcribes the audio into text, and the copies the text to the clipboard.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    #url='https://github.com/yourusername/your_project',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
