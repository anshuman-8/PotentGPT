import React from 'react'

export default function Details({prompt, id ,time, count}) {
  return (
    <div className='my-5'>
        <h2 className='font-semibold text-lg'>Details</h2>
        <div className='flex justify-start space-x-10'>

        <h3>Id: {id}</h3>
        <h3>Time (seconds) : {time}</h3>
        <h3>No. of Results : {count}</h3>
        </div>
    </div>
  )
}
