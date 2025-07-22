'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles, Zap, Trophy, Users } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export default function HomePage() {
  const [creationCount, setCreationCount] = useState(150234)
  const [activeUsers, setActiveUsers] = useState(45678)
  const [todayRevenue, setTodayRevenue] = useState(125678.90)

  // Fetch real stats
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/stats`)
      return response.data
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  // Animate counters
  useEffect(() => {
    if (stats) {
      setCreationCount(stats.total_creations)
      setActiveUsers(stats.active_users)
      setTodayRevenue(stats.revenue_today)
    }
  }, [stats])

  // Increment counters for live effect
  useEffect(() => {
    const interval = setInterval(() => {
      setCreationCount(prev => prev + Math.floor(Math.random() * 3))
      setActiveUsers(prev => prev + Math.floor(Math.random() * 2))
      setTodayRevenue(prev => prev + (Math.random() * 10))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const trendingChallenges = stats?.trending_challenges || [
    "#AIMoviePoster",
    "#PetAdventureAI",
    "#AITimeMachine"
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-pink-900">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/50" />
        
        {/* Animated background particles */}
        <div className="absolute inset-0">
          {[...Array(50)].map((_, i) => (
            <motion.div
              key={i}
              className="absolute w-1 h-1 bg-white rounded-full"
              initial={{
                x: Math.random() * (typeof window !== 'undefined' ? window.innerWidth : 1920),
                y: Math.random() * (typeof window !== 'undefined' ? window.innerHeight : 1080),
                opacity: Math.random(),
              }}
              animate={{
                y: [null, -100],
                opacity: [null, 0],
              }}
              transition={{
                duration: Math.random() * 10 + 5,
                repeat: Infinity,
                ease: "linear",
              }}
            />
          ))}
        </div>

        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-6xl md:text-8xl font-bold text-white mb-6">
              Create<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">.ai</span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Transform your ideas into viral content in under 30 seconds with AI
            </p>

            {/* Launch Special Badge */}
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-yellow-400 to-orange-400 text-black px-4 py-2 rounded-full font-bold mb-8"
            >
              <Zap className="w-5 h-5" />
              LAUNCH SPECIAL: 50% OFF ALL PLANS
            </motion.div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
              <Link href="/create">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-8 py-4 rounded-full font-bold text-lg flex items-center gap-2 hover:shadow-2xl hover:shadow-purple-500/50 transition-shadow"
                >
                  Start Creating <ArrowRight className="w-5 h-5" />
                </motion.button>
              </Link>
              
              <button className="bg-white/10 backdrop-blur text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-white/20 transition-colors">
                Watch Demo
              </button>
            </div>

            {/* Live Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-white/10 backdrop-blur rounded-xl p-6"
              >
                <Sparkles className="w-8 h-8 text-purple-400 mb-2 mx-auto" />
                <div className="text-3xl font-bold text-white">
                  {creationCount.toLocaleString()}
                </div>
                <div className="text-gray-400">Creations Made</div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="bg-white/10 backdrop-blur rounded-xl p-6"
              >
                <Users className="w-8 h-8 text-pink-400 mb-2 mx-auto" />
                <div className="text-3xl font-bold text-white">
                  {activeUsers.toLocaleString()}
                </div>
                <div className="text-gray-400">Active Creators</div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="bg-white/10 backdrop-blur rounded-xl p-6"
              >
                <Trophy className="w-8 h-8 text-yellow-400 mb-2 mx-auto" />
                <div className="text-3xl font-bold text-white">
                  ${todayRevenue.toLocaleString()}
                </div>
                <div className="text-gray-400">Revenue Today</div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Hero Video */}
      <section className="relative py-20">
        <div className="max-w-6xl mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8 }}
            className="relative rounded-2xl overflow-hidden shadow-2xl"
          >
            <div className="aspect-video bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center">
              <div className="text-white text-center">
                <div className="text-6xl mb-4">▶️</div>
                <p className="text-xl">Watch 30-Second Creation Process</p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Trending Challenges */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-white text-center mb-12">
            Trending Challenges
          </h2>
          
          <div className="flex flex-wrap justify-center gap-4">
            {trendingChallenges.map((challenge, index) => (
              <motion.div
                key={challenge}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ scale: 1.05 }}
                className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 backdrop-blur border border-white/20 rounded-full px-6 py-3 text-white font-semibold hover:border-white/40 transition-colors cursor-pointer"
              >
                {challenge}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Scrolling Gallery */}
      <section className="py-20 overflow-hidden">
        <h2 className="text-4xl font-bold text-white text-center mb-12">
          Top Creations
        </h2>
        
        <div className="relative">
          <motion.div
            animate={{ x: [0, -1920] }}
            transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
            className="flex gap-6"
          >
            {[...Array(20)].map((_, i) => (
              <div
                key={i}
                className="flex-shrink-0 w-80 h-80 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl"
              />
            ))}
          </motion.div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4">
          <h2 className="text-4xl font-bold text-white text-center mb-12">
            Simple Pricing, Powerful Results
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Basic Plan */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="bg-white/10 backdrop-blur rounded-2xl p-8 border border-white/20"
            >
              <div className="text-purple-400 font-bold mb-2">BASIC</div>
              <div className="text-4xl font-bold text-white mb-4">$9.99<span className="text-lg font-normal">/mo</span></div>
              <ul className="text-gray-300 space-y-3 mb-8">
                <li>✓ Unlimited creations</li>
                <li>✓ All AI models</li>
                <li>✓ Join challenges</li>
                <li>✓ Basic support</li>
              </ul>
              <button className="w-full bg-purple-500 text-white py-3 rounded-full font-bold hover:bg-purple-600 transition-colors">
                Get Started
              </button>
            </motion.div>

            {/* Pro Pack */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 backdrop-blur rounded-2xl p-8 border border-pink-500 relative"
            >
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-1 rounded-full text-sm font-bold">
                MOST POPULAR
              </div>
              <div className="text-pink-400 font-bold mb-2">PRO PACK</div>
              <div className="text-4xl font-bold text-white mb-4">$49.99<span className="text-lg font-normal">/100</span></div>
              <ul className="text-gray-300 space-y-3 mb-8">
                <li>✓ 100 creations</li>
                <li>✓ Priority processing</li>
                <li>✓ Create challenges</li>
                <li>✓ Advanced analytics</li>
              </ul>
              <button className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-full font-bold hover:shadow-lg transition-shadow">
                Get Pro Pack
              </button>
            </motion.div>

            {/* Business */}
            <motion.div
              whileHover={{ scale: 1.05 }}
              className="bg-white/10 backdrop-blur rounded-2xl p-8 border border-white/20"
            >
              <div className="text-yellow-400 font-bold mb-2">BUSINESS</div>
              <div className="text-4xl font-bold text-white mb-4">$499<span className="text-lg font-normal">/mo</span></div>
              <ul className="text-gray-300 space-y-3 mb-8">
                <li>✓ Unlimited everything</li>
                <li>✓ API access</li>
                <li>✓ Custom branding</li>
                <li>✓ Dedicated support</li>
              </ul>
              <button className="w-full bg-yellow-500 text-black py-3 rounded-full font-bold hover:bg-yellow-400 transition-colors">
                Contact Sales
              </button>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 text-center text-gray-400">
          <p>&copy; 2024 Create.ai - Transform Ideas Into Viral Content</p>
          <p className="mt-2">Built for the $20M Sprint Challenge</p>
        </div>
      </footer>
    </div>
  )
}
