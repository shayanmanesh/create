'use client'

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { 
  Sparkles, Upload, Mic, Image as ImageIcon, Type, 
  Loader2, Share2, Download, CheckCircle, AlertCircle,
  Zap, Clock, DollarSign
} from 'lucide-react'
import { useMutation, useQuery } from '@tanstack/react-query'
import axios from 'axios'
import Link from 'next/link'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

type InputType = 'text' | 'audio' | 'image'
type CreationType = 'general' | 'movie_poster' | 'pet_adventure' | 'time_machine' | 'dream_job' | 'love_story'

interface Creation {
  creation_id: string
  status: 'processing' | 'completed' | 'failed'
  content_url?: string
  share_links: {
    tiktok: string
    instagram: string
    twitter: string
    youtube: string
  }
  processing_time: number
  price: number
}

export default function CreatePage() {
  const [inputType, setInputType] = useState<InputType>('text')
  const [creationType, setCreationType] = useState<CreationType>('general')
  const [textInput, setTextInput] = useState('')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [creation, setCreation] = useState<Creation | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)

  // Get pricing info
  const { data: pricing } = useQuery({
    queryKey: ['pricing'],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/pricing`)
      return response.data
    },
  })

  const surgeActive = pricing?.pricing?.single?.surge_active || false
  const currentPrice = pricing?.pricing?.single?.current_price || 0.99

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: FormData) => {
      const response = await axios.post(`${API_URL}/creations/create`, data, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
      return response.data
    },
    onSuccess: (data) => {
      setCreation(data)
      // Start polling for completion
      pollCreationStatus(data.creation_id)
    },
  })

  // Poll for creation status
  const pollCreationStatus = async (creationId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/creations/${creationId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          },
        })
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          clearInterval(interval)
          setCreation(prev => ({ ...prev!, ...response.data }))
        }
      } catch (error) {
        console.error('Error polling status:', error)
      }
    }, 2000)
  }

  // File upload handler
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setUploadedFile(acceptedFiles[0])
      const fileType = acceptedFiles[0].type
      
      if (fileType.startsWith('image/')) {
        setInputType('image')
      } else if (fileType.startsWith('audio/')) {
        setInputType('audio')
      }
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
      'audio/*': ['.mp3', '.wav', '.m4a'],
    },
    maxFiles: 1,
  })

  // Handle creation submission
  const handleCreate = async () => {
    const formData = new FormData()
    formData.append('input_type', inputType)
    formData.append('creation_type', creationType)
    formData.append('language', 'en')

    if (inputType === 'text') {
      formData.append('text_input', textInput)
    } else if (inputType === 'audio' && (uploadedFile || audioBlob)) {
      formData.append('file', uploadedFile || audioBlob as File)
    } else if (inputType === 'image' && uploadedFile) {
      formData.append('file', uploadedFile)
    }

    createMutation.mutate(formData)
  }

  // Record audio
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      const chunks: Blob[] = []

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data)
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        setAudioBlob(blob)
        setUploadedFile(new File([blob], 'recording.webm', { type: 'audio/webm' }))
      }

      mediaRecorder.start()
      setIsRecording(true)

      // Stop after 30 seconds
      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
          stream.getTracks().forEach(track => track.stop())
          setIsRecording(false)
        }
      }, 30000)
    } catch (error) {
      console.error('Error accessing microphone:', error)
    }
  }

  const creationTypes = [
    { id: 'general', name: 'General', icon: Sparkles },
    { id: 'movie_poster', name: 'Movie Poster', icon: ImageIcon },
    { id: 'pet_adventure', name: 'Pet Adventure', icon: Sparkles },
    { id: 'time_machine', name: 'Time Machine', icon: Clock },
    { id: 'dream_job', name: 'Dream Job', icon: Sparkles },
    { id: 'love_story', name: 'Love Story', icon: Sparkles },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-pink-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/" className="text-2xl font-bold">
            Create<span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">.ai</span>
          </Link>
          
          {surgeActive && (
            <div className="flex items-center gap-2 bg-yellow-500/20 border border-yellow-500 text-yellow-300 px-4 py-2 rounded-full">
              <Zap className="w-4 h-4" />
              <span className="text-sm font-medium">Surge Pricing Active</span>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {!creation ? (
          <>
            {/* Creation Type Selection */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Choose Creation Type</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {creationTypes.map(type => (
                  <motion.button
                    key={type.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setCreationType(type.id as CreationType)}
                    className={`p-4 rounded-xl border transition-all ${
                      creationType === type.id
                        ? 'bg-purple-500/20 border-purple-500 text-purple-300'
                        : 'bg-white/5 border-white/20 text-gray-300 hover:bg-white/10'
                    }`}
                  >
                    <type.icon className="w-8 h-8 mb-2 mx-auto" />
                    <div className="font-medium">{type.name}</div>
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Input Type Selection */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Input Method</h2>
              <div className="flex gap-4 mb-6">
                <button
                  onClick={() => setInputType('text')}
                  className={`px-6 py-3 rounded-full font-medium transition-all ${
                    inputType === 'text'
                      ? 'bg-purple-500 text-white'
                      : 'bg-white/10 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  <Type className="w-5 h-5 inline mr-2" />
                  Text
                </button>
                <button
                  onClick={() => setInputType('audio')}
                  className={`px-6 py-3 rounded-full font-medium transition-all ${
                    inputType === 'audio'
                      ? 'bg-purple-500 text-white'
                      : 'bg-white/10 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  <Mic className="w-5 h-5 inline mr-2" />
                  Voice
                </button>
                <button
                  onClick={() => setInputType('image')}
                  className={`px-6 py-3 rounded-full font-medium transition-all ${
                    inputType === 'image'
                      ? 'bg-purple-500 text-white'
                      : 'bg-white/10 text-gray-300 hover:bg-white/20'
                  }`}
                >
                  <ImageIcon className="w-5 h-5 inline mr-2" />
                  Image
                </button>
              </div>

              {/* Input Area */}
              <div className="bg-white/5 backdrop-blur rounded-2xl p-8 border border-white/10">
                {inputType === 'text' ? (
                  <textarea
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    placeholder="Describe your idea in detail..."
                    className="w-full h-40 bg-white/10 border border-white/20 rounded-xl p-4 text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 transition-colors"
                  />
                ) : inputType === 'audio' ? (
                  <div className="text-center">
                    {!audioBlob && !uploadedFile ? (
                      <>
                        <button
                          onClick={startRecording}
                          disabled={isRecording}
                          className={`mb-4 px-8 py-4 rounded-full font-medium transition-all ${
                            isRecording
                              ? 'bg-red-500 text-white animate-pulse'
                              : 'bg-purple-500 text-white hover:bg-purple-600'
                          }`}
                        >
                          {isRecording ? (
                            <>
                              <Mic className="w-5 h-5 inline mr-2 animate-pulse" />
                              Recording... (max 30s)
                            </>
                          ) : (
                            <>
                              <Mic className="w-5 h-5 inline mr-2" />
                              Start Recording
                            </>
                          )}
                        </button>
                        <div className="text-gray-400 mb-4">OR</div>
                      </>
                    ) : (
                      <div className="mb-4 p-4 bg-green-500/20 border border-green-500 rounded-xl text-green-300">
                        <CheckCircle className="w-5 h-5 inline mr-2" />
                        Audio recorded successfully
                      </div>
                    )}
                  </div>
                ) : null}

                {/* File Upload Area */}
                {(inputType === 'audio' || inputType === 'image') && (
                  <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                      isDragActive
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-white/20 hover:border-white/40'
                    }`}
                  >
                    <input {...getInputProps()} />
                    <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                    {uploadedFile ? (
                      <p className="text-green-400">
                        <CheckCircle className="w-5 h-5 inline mr-2" />
                        {uploadedFile.name}
                      </p>
                    ) : (
                      <p className="text-gray-400">
                        Drag & drop or click to upload
                        {inputType === 'audio' ? ' audio' : ' image'}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Create Button */}
            <div className="text-center">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleCreate}
                disabled={
                  createMutation.isPending ||
                  (inputType === 'text' && !textInput) ||
                  ((inputType === 'audio' || inputType === 'image') && !uploadedFile && !audioBlob)
                }
                className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-12 py-4 rounded-full font-bold text-lg disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-2xl hover:shadow-purple-500/50 transition-all"
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="w-5 h-5 inline mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5 inline mr-2" />
                    Create Now
                    {currentPrice > 0 && (
                      <span className="ml-2 text-sm opacity-80">
                        ${currentPrice.toFixed(2)}
                        {surgeActive && ' (surge)'}
                      </span>
                    )}
                  </>
                )}
              </motion.button>
            </div>
          </>
        ) : (
          /* Creation Result */
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="max-w-4xl mx-auto"
            >
              {/* Status */}
              <div className="text-center mb-8">
                {creation.status === 'processing' ? (
                  <>
                    <Loader2 className="w-16 h-16 mx-auto mb-4 text-purple-400 animate-spin" />
                    <h2 className="text-3xl font-bold mb-2">Creating Your Content...</h2>
                    <p className="text-gray-400">This usually takes less than 30 seconds</p>
                    <div className="mt-4 flex justify-center gap-2">
                      {[...Array(3)].map((_, i) => (
                        <motion.div
                          key={i}
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                          className="w-3 h-3 bg-purple-400 rounded-full"
                        />
                      ))}
                    </div>
                  </>
                ) : creation.status === 'completed' ? (
                  <>
                    <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-400" />
                    <h2 className="text-3xl font-bold mb-2">Creation Complete!</h2>
                    <p className="text-gray-400">
                      Created in {creation.processing_time.toFixed(1)} seconds
                    </p>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-16 h-16 mx-auto mb-4 text-red-400" />
                    <h2 className="text-3xl font-bold mb-2">Creation Failed</h2>
                    <p className="text-gray-400">Something went wrong. Please try again.</p>
                  </>
                )}
              </div>

              {/* Content Preview */}
              {creation.status === 'completed' && (
                <div className="bg-white/5 backdrop-blur rounded-2xl p-8 border border-white/10 mb-8">
                  <div className="aspect-video bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl mb-6" />
                  
                  {/* Action Buttons */}
                  <div className="flex gap-4 justify-center">
                    <button className="bg-purple-500 text-white px-6 py-3 rounded-full font-medium hover:bg-purple-600 transition-colors">
                      <Download className="w-5 h-5 inline mr-2" />
                      Download
                    </button>
                    
                    {/* Share Buttons */}
                    <div className="flex gap-2">
                      {Object.entries(creation.share_links).map(([platform, link]) => (
                        <a
                          key={platform}
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="bg-white/10 text-white p-3 rounded-full hover:bg-white/20 transition-colors"
                        >
                          <Share2 className="w-5 h-5" />
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Create Another */}
              <div className="text-center">
                <button
                  onClick={() => {
                    setCreation(null)
                    setTextInput('')
                    setUploadedFile(null)
                    setAudioBlob(null)
                  }}
                  className="text-purple-400 hover:text-purple-300 font-medium"
                >
                  Create Another
                </button>
              </div>
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}