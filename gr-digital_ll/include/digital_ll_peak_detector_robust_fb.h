/* -*- c++ -*- */
/*
 * This file is part of ExtRaSy
 *
 * Copyright (C) 2013-2014 Massachusetts Institute of Technology
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 */

#ifndef INCLUDED_DIGITAL_LL_PEAK_DETECTOR_ROBUST_FB_H
#define INCLUDED_DIGITAL_LL_PEAK_DETECTOR_ROBUST_FB_H

#include <digital_ll_api.h>
#include <gr_sync_block.h>

class digital_ll_peak_detector_robust_fb;
typedef boost::shared_ptr<digital_ll_peak_detector_robust_fb> digital_ll_peak_detector_robust_fb_sptr;

DIGITAL_LL_API digital_ll_peak_detector_robust_fb_sptr digital_ll_make_peak_detector_robust_fb (float threshold_factor_rise = 0.25, float threshold_factor_fall = 0.40, int look_ahead = 10, float alpha = 0.001);

/*!
 * \brief Detect the peak of a signal
 * \ingroup level_blk
 *
 * If a peak is detected, this block outputs a 1,
 * or it outputs 0's.
 *
 * \param threshold_factor_rise The threshold factor determins when a peak
 *        has started. An average of the signal is calculated and when the
 *        value of the signal goes over threshold_factor_rise*average, we
 *        start looking for a peak.
 * \param threshold_factor_fall The threshold factor determins when a peak
 *        has ended. An average of the signal is calculated and when the
 *        value of the signal goes bellow threshold_factor_fall*average, we
 *        stop looking for a peak.
 * \param look_ahead The look-ahead value is used when the threshold is
 *        found to look if there another peak within this step range.
 *        If there is a larger value, we set that as the peak and look ahead
 *        again. This is continued until the highest point is found with
 *        This look-ahead range.
 * \param alpha The gain value of a moving average filter
 */
class DIGITAL_LL_API digital_ll_peak_detector_robust_fb : public gr_sync_block
{
	friend DIGITAL_LL_API digital_ll_peak_detector_robust_fb_sptr digital_ll_make_peak_detector_robust_fb 
        (float threshold_factor_rise, 
        float threshold_factor_fall, 
        int look_ahead, 
        float alpha);

	digital_ll_peak_detector_robust_fb 
        (float threshold_factor_rise, 
        float threshold_factor_fall, 
        int look_ahead, 
        float alpha);

 private:
  float d_threshold_factor_rise;
  float d_threshold_factor_fall;
  int d_look_ahead;
  float d_avg_alpha;
  float d_avg;
  unsigned char d_found;

 public:
	
  /*! \brief Set the threshold factor value for the rise time
   *  \param thr new threshold factor
   */
  void set_threshold_factor_rise(float thr) { d_threshold_factor_rise = thr; }

  /*! \brief Set the threshold factor value for the fall time
   *  \param thr new threshold factor
   */
  void set_threshold_factor_fall(float thr) { d_threshold_factor_fall = thr; }

  /*! \brief Set the look-ahead factor
   *  \param look new look-ahead factor
   */
  void set_look_ahead(int look) { d_look_ahead = look; }

  /*! \brief Set the running average alpha
   *  \param alpha new alpha for running average
   */
  void set_alpha(int alpha) { d_avg_alpha = alpha; }

  /*! \brief Get the threshold factor value for the rise time
   *  \return threshold factor
   */
  float threshold_factor_rise() { return d_threshold_factor_rise; }

  /*! \brief Get the threshold factor value for the fall time
   *  \return threshold factor
   */
  float threshold_factor_fall() { return d_threshold_factor_fall; }

  /*! \brief Get the look-ahead factor value
   *  \return look-ahead factor
   */
  int look_ahead() { return d_look_ahead; }

  /*! \brief Get the alpha value of the running average
   *  \return alpha
   */
  float alpha() { return d_avg_alpha; }

  int work (int noutput_items,
		gr_vector_const_void_star &input_items,
		gr_vector_void_star &output_items);
};

#endif /* INCLUDED_DIGITAL_LL_PEAK_DETECTOR_ROBUST_FB_H */

