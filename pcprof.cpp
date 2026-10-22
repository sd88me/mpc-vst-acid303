// Minimal sampling profiler for the Force (no perf there): SIGPROF every 1 ms of CPU time
// records the interrupted PC; at exit the counts go to pcprof.txt as "count hexaddr".
// Link it in and run; symbolise with addr2line on the host (prof2.sh).
#include <csignal>
#include <cstdio>
#include <map>
#include <sys/time.h>
#include <ucontext.h>

namespace {
constexpr int kMax = 1 << 20;
unsigned long g_pcs[kMax];
volatile int g_n = 0;

void onProf(int, siginfo_t *, void *ctx)
{
	if (g_n < kMax)
#if defined(__arm__)
		g_pcs[g_n++] = static_cast<ucontext_t *>(ctx)->uc_mcontext.arm_pc;
#else
		g_pcs[g_n++] = static_cast<ucontext_t *>(ctx)->uc_mcontext.gregs[REG_RIP];
#endif
}

struct Profiler {
	Profiler()
	{
		struct sigaction sa = {};
		sa.sa_sigaction = onProf;
		sa.sa_flags = SA_SIGINFO | SA_RESTART;
		sigaction(SIGPROF, &sa, nullptr);
		itimerval t = {{0, 1000}, {0, 1000}};
		setitimer(ITIMER_PROF, &t, nullptr);
	}
	~Profiler()
	{
		itimerval t = {};
		setitimer(ITIMER_PROF, &t, nullptr);
		std::map<unsigned long, int> c;
		for (int i = 0; i < g_n; ++i)
			++c[g_pcs[i]];
		FILE *f = fopen("pcprof.txt", "w");
		for (auto &kv : c)
			fprintf(f, "%d %lx\n", kv.second, kv.first);
		fclose(f);
	}
} g_profiler;
} // namespace
