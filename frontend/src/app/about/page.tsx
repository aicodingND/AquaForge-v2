import Link from 'next/link';

export default function AboutPage() {
  return (
    <div className="p-6 lg:p-8 space-y-8">
      {/* Hero Section */}
      <div className="glass-card p-8 lg:p-12 text-center">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[var(--gold-400)] to-[var(--gold-500)] flex items-center justify-center font-bold text-[var(--navy-900)] text-3xl shadow-lg">
          A
        </div>
        <h1 className="text-3xl lg:text-4xl font-bold text-white mb-4">
          About <span className="gradient-text-gold">AquaForge</span>
        </h1>
        <p className="text-white/60 text-lg max-w-2xl mx-auto">
          AI-powered swim meet optimization that gives your team the competitive edge
        </p>
      </div>

      {/* Mission */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <span className="text-[var(--gold-400)]">🎯</span> Our Mission
          </h2>
          <p className="text-white/70 leading-relaxed">
            AquaForge was created to level the playing field for swim teams of all sizes. 
            Using advanced optimization algorithms, we help coaches make data-driven decisions 
            for lineup assignments, event entries, and strategic meet planning.
          </p>
        </div>

        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <span className="text-[var(--gold-400)]">⚡</span> The Technology
          </h2>
          <p className="text-white/70 leading-relaxed">
            Our platform combines heuristic algorithms for fast approximations with 
            industrial-grade Gurobi optimization for mathematically optimal solutions. 
            We handle complex constraints like fatigue modeling, back-to-back rules, and event limits.
          </p>
        </div>
      </div>

      {/* Features */}
      <div className="glass-card p-6">
        <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
          <span className="text-[var(--gold-400)]">✨</span> Key Features
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { icon: '📊', title: 'Score Optimization', desc: 'Maximize team points with optimal lineup assignments' },
            { icon: '🏊', title: 'Dual Meet Mode', desc: 'Head-to-head optimization for dual meet scoring' },
            { icon: '🏆', title: 'Championship Mode', desc: 'Multi-team meets with psych sheet integration' },
            { icon: '🔄', title: 'Relay Optimization', desc: 'Optimal relay leg assignments for medley and free relays' },
            { icon: '⏱️', title: 'Fatigue Modeling', desc: 'Smart constraints for back-to-back event management' },
            { icon: '📈', title: 'Analytics Dashboard', desc: 'Team comparison and performance insights' },
          ].map((feature, i) => (
            <div key={i} className="p-4 bg-[var(--navy-700)] rounded-lg">
              <div className="text-2xl mb-2">{feature.icon}</div>
              <h3 className="font-medium text-white mb-1">{feature.title}</h3>
              <p className="text-sm text-white/50">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div className="text-center">
        <Link href="/meet" className="btn btn-gold btn-lg">
          Get Started →
        </Link>
      </div>
    </div>
  );
}
