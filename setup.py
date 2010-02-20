try:
    from setuptools import setup, find_packages
except ImportError:
    from distribute_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='WebUndo',
    version='0.1',
    description="Gmail's undo/cancel web feature, for Pylons and other frameworks",
    author='Alexandre Bourget',
    author_email='alex@bourget.cc',
    url='http://blog.abourget.net',
    install_requires=[],
    packages=find_packages(exclude=['distribute_setup']),
    include_package_data=True,
    zip_safe=False,
    entry_points="""
    """,
)
