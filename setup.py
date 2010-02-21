try:
    from setuptools import setup
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup

setup(
    name='WebUndo',
    version='0.1',
    description="Gmail's undo/cancel web feature, for Pylons and other frameworks",
    author='Alexandre Bourget',
    author_email='alex@bourget.cc',
    url='http://webundo.abourget.net',
    install_requires=[],
    packages=['webundo'],
    zip_safe=False,
    entry_points="""
    """,
)
