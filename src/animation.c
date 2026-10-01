// @file animation.c
// @brief Animation framework to animate pointer values
//
// Animation framework to animate a pointer's value. A value can have several
// animations at once (the newest one that is running sets the value); a caller
// that replaces an animation stops the old one first with animation_stop().
// Animations also auto-destruct when complete. If the heap is full, the value
// is set to its end at once and no animation runs.
//
// @author Eric D. Phillips
// @date September 1, 2015
// @bugs No known bugs

#include "animation.h"
#include "utility.h"

// Animation constants
#define ANIMATION_TICK_INTERVAL 30      //< Number of milliseconds to pause between animation ticks

// The value an animation moves from or to
typedef union {
  GRect   grect;
  int32_t int32;
} AnimationValue;

// Animation pointer type. One allocation holds the whole animation, so that it
// uses little heap (aplite has about 2KB) and has one point of failure.
typedef struct AnimationNode {
  void (*step_func)(struct AnimationNode*);   //< Function to call when stepping animation
  void                    *target;            //< Pointer to value being animated
  AnimationValue          from;               //< Value to animate from (see has_from)
  AnimationValue          to;                 //< Value to animate to
  uint64_t                start_time;         //< Millisecond epoch of when animation was started
  uint32_t                duration;           //< Duration of animation in milliseconds
  uint32_t                delay;              //< Time to wait before animating
  InterpolationCurve      interpolation;      //< The interpolation mode to use with this animation
  bool                    has_from;           //< False until the first step reads the from value
  struct AnimationNode    *next;              //< Pointer to next node in linked list
} AnimationNode;

// Animation framework data
static AnimationNode  *head_node = NULL;      //< Head node in linked list containing all animations
static AppTimer       *ani_timer = NULL;      //< AppTimer for stepping all animations
static void   (*ani_callback)(void) = NULL;   //< Animation update callback

// Functions
static void prv_animation_timer_start(void);

////////////////////////////////////////////////////////////////////////////////////////////////////
// Private Functions
//

// Step a GRect animation
static void prv_animation_step_grect(AnimationNode *node) {
  // set from grect on first call, allowing another animation to change the target value
  // while this animation is delayed
  if (!node->has_from) {
    node->has_from = true;
    node->from.grect = (*(GRect*)node->target);
  }
  // step value
  GRect from = node->from.grect;
  GRect to = node->to.grect;
  uint32_t percent_max = node->duration;
  uint32_t percent = epoch() - (node->start_time + node->delay);
  (*(GRect*)node->target).origin.x = interpolation_integer(from.origin.x, to.origin.x, percent,
    percent_max, node->interpolation);
  (*(GRect*)node->target).origin.y = interpolation_integer(from.origin.y, to.origin.y, percent,
    percent_max, node->interpolation);
  (*(GRect*)node->target).size.w = interpolation_integer(from.size.w, to.size.w, percent,
    percent_max, node->interpolation);
  (*(GRect*)node->target).size.h = interpolation_integer(from.size.h, to.size.h, percent,
    percent_max, node->interpolation);
  // continue animation
  if (percent >= percent_max) {
    animation_stop(node->target);
  }
}

// Step a int32 animation
static void prv_animation_step_int32(AnimationNode *node) {
  // set from value on first call, allowing another animation to change the target value
  // while this animation is delayed
  if (!node->has_from) {
    node->has_from = true;
    node->from.int32 = (*(int32_t*)node->target);
  }
  // step value
  uint32_t percent_max = node->duration;
  uint32_t percent = epoch() - (node->start_time + node->delay);
  (*(int32_t*)node->target) = interpolation_integer(node->from.int32, node->to.int32, percent,
    percent_max, node->interpolation);
  // continue animation
  if (percent >= percent_max) {
    animation_stop(node->target);
  }
}

// Create a node (not yet in the list). Returns NULL when the heap is full:
// the caller then sets the value to its end, so a full heap costs only the
// motion and never stops the app.
static AnimationNode *prv_node_create(void (*step_func)(AnimationNode*), void *target,
                                      uint32_t duration, uint32_t delay,
                                      InterpolationCurve interpolation) {
  AnimationNode *new_node = (AnimationNode*)malloc(sizeof(AnimationNode));
  if (!new_node) {
    return NULL;
  }
  new_node->step_func = step_func;
  new_node->target = target;
  new_node->has_from = false; // assigned on first "step" callback in case of delayed animation
  new_node->start_time = epoch();
  new_node->duration = duration;
  new_node->delay = delay;
  new_node->interpolation = interpolation;
  new_node->next = NULL;
  return new_node;
}

// Add node to end of linked list
static void prv_list_add_node(AnimationNode *node) {
  if (!head_node) {
    head_node = node;
    return;
  }
  AnimationNode *cur_node = head_node;
  while (cur_node->next) {
    cur_node = cur_node->next;
  }
  cur_node->next = node;
}

// Animation timer callback
static void prv_animation_timer_callback(void *data) {
  ani_timer = NULL;
  // loop over list and step each animation
  AnimationNode *cur_node = head_node;
  while (cur_node) {
    // a step that ends its animation frees a node, which can be cur_node
    AnimationNode *next_node = cur_node->next;
    if (epoch() > cur_node->start_time + (uint64_t)cur_node->delay) {
      (*cur_node->step_func)(cur_node);
    }
    cur_node = next_node;
  }
  // continue animation
  if (head_node) {
    prv_animation_timer_start();
  }
  // raise animation update callback
  if (ani_callback) {
    ani_callback();
  }
}

// Start animation timer if not running
static void prv_animation_timer_start(void) {
  if (!ani_timer) {
    ani_timer = app_timer_register(ANIMATION_TICK_INTERVAL, &prv_animation_timer_callback, NULL);
  }
}


////////////////////////////////////////////////////////////////////////////////////////////////////
// API Functions
//

// Animate a GRect by its pointer
void animation_grect_start(GRect *ptr, GRect to, uint32_t duration, uint32_t delay,
                           InterpolationCurve interpolation) {
  // create and add new node
  AnimationNode *new_node = prv_node_create(&prv_animation_step_grect, ptr, duration, delay,
    interpolation);
  if (!new_node) {
    (*ptr) = to;
    return;
  }
  new_node->to.grect = to;
  prv_list_add_node(new_node);
  // start animation timer if not running
  prv_animation_timer_start();
}

// Animate an integer by its pointer
void animation_int32_start(int32_t *ptr, int32_t to, uint32_t duration, uint32_t delay,
                           InterpolationCurve interpolation) {
  // create and add new node
  AnimationNode *new_node = prv_node_create(&prv_animation_step_int32, ptr, duration, delay,
    interpolation);
  if (!new_node) {
    (*ptr) = to;
    return;
  }
  new_node->to.int32 = to;
  prv_list_add_node(new_node);
  // start animation timer if not running
  prv_animation_timer_start();
}

// Cancel an animation by its pointer
void animation_stop(void *ptr) {
  AnimationNode *cur_node = head_node;
  AnimationNode *pre_node = NULL;
  while (cur_node) {
    if (cur_node->target == ptr) {
      // link surrounding nodes
      if (pre_node) {
        pre_node->next = cur_node->next;
      } else {
        head_node = cur_node->next;
      }
      // destroy node
      free(cur_node);
      return;
    }
    pre_node = cur_node;
    cur_node = cur_node->next;
  }
}

// Cancel all running animations
void animation_stop_all(void) {
  // stop timer
  if (ani_timer) {
    app_timer_cancel(ani_timer);
    ani_timer = NULL;
  }
  // destroy all animations
  AnimationNode *cur_node = head_node;
  AnimationNode *tmp_node = NULL;
  head_node = NULL;
  while (cur_node) {
    // index node
    tmp_node = cur_node;
    cur_node = cur_node->next;
    // destroy node
    free(tmp_node);
  }
}

// Register animation update callback
void animation_register_update_callback(void *callback) {
  ani_callback = callback;
}
