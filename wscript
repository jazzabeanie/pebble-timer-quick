
#
# This file is the default set of rules to compile a Pebble project.
#
# Feel free to customize this to your needs.
#

import os.path

top = '.'
out = 'build'

def options(ctx):
    ctx.load('pebble_sdk')
    ctx.load('compiler_c')

def configure(ctx):
    ctx.load('pebble_sdk')
    
    # Setup Host Environment
    # We derive from current to keep basics, but we will overwrite compiler
    host_env = ctx.env.derive()
    ctx.all_envs['host'] = host_env
    ctx.set_env(host_env)
    
    ctx.load('compiler_c') # Should find GCC for host
    
    # Check for local cmocka
    import os
    cmocka_root = os.path.abspath('vendor/cmocka_install')
    cmocka_include = os.path.join(cmocka_root, 'include')
    cmocka_lib = os.path.join(cmocka_root, 'lib')
    
    if os.path.exists(os.path.join(cmocka_include, 'cmocka.h')):
        print("Found local cmocka at {}".format(cmocka_root))
        ctx.env.HAVE_CMOCKA = 1
        ctx.env.INCLUDES_CMOCKA = [cmocka_include]
        ctx.env.LIBPATH_CMOCKA = [cmocka_lib]
        ctx.env.LIB_CMOCKA = ['cmocka']
        ctx.env.CMOCKA_ROOT = cmocka_root
    else:
        try:
            ctx.check_cfg(package='cmocka', args='--cflags --libs', uselib_store='CMOCKA', mandatory=False)
        except Exception as e:
            print("Warning: cmocka not found. Tests might fail to build.")

    # Switch back to default env
    if '' in ctx.all_envs:
        ctx.set_env(ctx.all_envs[''])

def build(ctx):
    ctx.load('pebble_sdk')

    # Load host environment
    if 'host' in ctx.all_envs:
        host_env = ctx.all_envs['host']
    else:
        host_env = ctx.env.derive()

    build_worker = os.path.exists('worker_src')
    binaries = []

    for p in ctx.env.TARGET_PLATFORMS:
        ctx.set_env(ctx.all_envs[p])
        ctx.set_group(ctx.env.PLATFORM_NAME)
        app_elf='{}/pebble-app.elf'.format(ctx.env.BUILD_DIR)
        ctx.pbl_program(source=ctx.path.ant_glob('src/**/*.c'),
        target=app_elf)

        if build_worker:
            worker_elf='{}/pebble-worker.elf'.format(ctx.env.BUILD_DIR)
            binaries.append({'platform': p, 'app_elf': app_elf, 'worker_elf': worker_elf})
            ctx.pbl_worker(source=ctx.path.ant_glob('worker_src/**/*.c'),
            target=worker_elf)
        else:
            binaries.append({'platform': p, 'app_elf': app_elf})

    ctx.set_group('bundle')
    ctx.pbl_bundle(binaries=binaries, js=ctx.path.ant_glob('src/js/**/*.js'))
    
    # Test Build
    if host_env.HAVE_CMOCKA:
        ctx.set_env(host_env)
        
        # Reconstruct cmocka include path
        cmocka_root = host_env.CMOCKA_ROOT
        cmocka_inc = os.path.join(cmocka_root, 'include')
        
        # Absolute paths
        test_dir = ctx.path.find_dir('test').abspath()
        src_dir = ctx.path.find_dir('src').abspath()
        
        print("Debug: Includes: {}, {}, {}".format(test_dir, src_dir, cmocka_inc))
        
        ctx.program(
            source=['test/test_timer.c', 'src/timer.c'],
            target='run_tests',
            includes=[test_dir, src_dir, cmocka_inc],
            use=['CMOCKA']
        )

def test(ctx):
    import os
    if os.path.exists('build/run_tests'):
        # Add local lib to LD_LIBRARY_PATH
        env = os.environ.copy()
        if ctx.env.CMOCKA_ROOT:
            lib_path = os.path.join(ctx.env.CMOCKA_ROOT, 'lib')
            env['LD_LIBRARY_PATH'] = lib_path + ':' + env.get('LD_LIBRARY_PATH', '')
        
        print("Running tests with LD_LIBRARY_PATH={}".format(env.get('LD_LIBRARY_PATH', '')))
        ctx.exec_command('build/run_tests', env=env)
    else:
        print("Test binary not found. Did cmocka library checks pass?")
