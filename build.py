def build(setup_kwargs):
    setup_kwargs.update(
        ext_modules=cythonize("nbtlib/tag.pyx", force=True),
        cmdclass={"build_ext": build_ext},
    )
